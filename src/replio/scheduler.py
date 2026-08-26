import sys
import time
import threading
from datetime import datetime, timezone

from .config import Config
from .engine import Engine, TurnResult
from .jobs import (Job, JobRun, JobRegistry, compute_next_run, parse_dt,
                   read_memory, system_prompt_for, write_memory)
from .ui import HeadlessUI


def _build_engine(config: Config, job: Job, verbose: bool,
                  stream: bool = False) -> Engine:
    sub_config = Config(path=str(config.local_path.parent.parent))
    persona = None
    if job.persona:
        from .personas import PersonaRegistry
        personas = PersonaRegistry(local_path=config.local_path.parent / 'personas.json')
        persona = personas.find(job.persona)
        if persona is None:
            raise ValueError(f'Unknown persona: {job.persona}')
        if persona.model:
            sub_config.apply('model', persona.model)
        permissions = dict(sub_config.get('tool_permission') or {})
        permissions.update(persona.tool_permission)
        sub_config.apply('tool_permission', permissions)
    try:
        system_text = system_prompt_for(job, config.local_path.parent.parent,
                                        persona)
    except FileNotFoundError as e:
        raise ValueError(str(e)) from e
    sub_config.apply('system_prompt', system_text)
    if job.mode:
        sub_config.apply('mode', job.mode)
    if job.provider:
        sub_config.apply('provider', job.provider)
    if job.model:
        sub_config.apply('model', job.model)
    if job.tool_permission:
        permissions = dict(sub_config.get('tool_permission') or {})
        permissions.update(job.tool_permission)
        sub_config.apply('tool_permission', permissions)
    if job.tools_deny:
        sub_config.apply('tools.deny', job.tools_deny)
    ui = HeadlessUI(auto='deny', verbose=verbose, stream=stream,
                    show_thinking=sub_config.get('show_thinking', True),
                    footer_tokens=sub_config.get('footer_tokens', ['context']))
    engine = Engine(sub_config, ui=ui)
    engine.load_or_create_session(job.session or f'job.{job.name}')
    return engine


def _attempt(engine: Engine, prompt: str, timeout: int) -> TurnResult:
    timeout = max(0, int(timeout or 0))
    if timeout <= 0:
        try:
            return engine.chat(prompt, autoname=False)
        except Exception as e:
            return TurnResult(status='error',
                              errors=[{'code': 0, 'message': str(e)}],
                              session=engine.current_session.name)
    bag: dict = {}

    def target():
        try:
            bag['value'] = engine.chat(prompt, autoname=False)
        except Exception as e:
            bag['error'] = e

    thread = threading.Thread(target=target,
                              name=f'job-{engine.current_session.name}',
                              daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        return TurnResult(status='error',
                          errors=[{'code': 'timeout',
                                   'message': f'job exceeded {timeout}s timeout'}],
                          session=engine.current_session.name)
    if 'error' in bag:
        return TurnResult(status='error',
                          errors=[{'code': 0, 'message': str(bag['error'])}],
                          session=engine.current_session.name)
    return bag['value']


class JobScheduler:
    def __init__(self, config: Config, verbose: bool = True,
                 stream: bool = False):
        self.config = config
        self.registry = JobRegistry(config.local_path.parent / 'jobs.json')
        self.verbose = verbose
        self.stream = stream

    def _out(self, msg: str, error: bool = False):
        stream = sys.stderr if error else sys.stdout
        if self.verbose:
            stream.write(f'[job] {msg}\n')
            stream.flush()

    def _maybe_compact(self, engine, job: Job):
        limit = max(0, int(job.max_context or 0))
        if limit <= 0:
            return
        try:
            size = len(engine._provider_messages())
        except AttributeError:
            return
        if size >= limit:
            engine.compact_session()
            self._out(f'{job.name}: auto-compacted context ({size} messages)')

    def run_job(self, job: Job) -> JobRun:
        job.status = 'executing'
        job.next_run_at = ''
        self.registry.save()
        retries = max(0, int(job.retries or 0))
        backoff = max(0.0, float(job.backoff or 0))
        attempt = 0
        last_run: JobRun | None = None
        finished = datetime.now(timezone.utc)
        while True:
            attempt += 1
            started = datetime.now(timezone.utc)
            try:
                engine = _build_engine(self.config, job, self.verbose,
                                       self.stream)
            except ValueError as e:
                run = JobRun(started_at=started.isoformat(timespec='seconds'),
                             finished_at=started.isoformat(timespec='seconds'),
                             status='failed', reason=str(e), attempt=attempt,
                             session=job.session or f'job.{job.name}')
                job.history.append(run)
                self.registry.save()
                self._finish(job, run, started)
                self._update_memory(None, job, run)
                return run
            if attempt == 1:
                self._maybe_compact(engine, job)
            if attempt > 1:
                prompt = (f'[Previous attempt {attempt - 1} failed. Retry this '
                          f'job and finish it.]\n\n{job.prompt}')
            else:
                prompt = job.prompt
            self._out(f'run {job.name} (attempt {attempt})')
            result = _attempt(engine, prompt, job.timeout)
            finished = datetime.now(timezone.utc)
            ok = result.status in ('ok', 'truncated')
            reason = ''
            if result.errors:
                reason = '; '.join(
                    e.get('message', '') for e in result.errors
                    if isinstance(e, dict) and e.get('message'))
                if len(reason) > 300:
                    reason = reason[:300] + '...'
            run = JobRun(
                started_at=started.isoformat(timespec='seconds'),
                finished_at=finished.isoformat(timespec='seconds'),
                status='verified' if ok else 'failed',
                reason=reason, duration=round(result.duration, 1),
                session=result.session or '', attempt=attempt,
                content=(result.content or '')[:1000])
            job.history.append(run)
            self.registry.save()
            if ok or attempt > retries:
                break
            delay = backoff * (2 ** (attempt - 1))
            self._out(f'attempt {attempt} failed - retrying in {delay:.0f}s '
                      f'(attempt {attempt}/{retries + 1})')
            if delay > 0:
                time.sleep(delay)
        self._finish(job, run, finished)
        self._update_memory(engine, job, run)
        return run

    def _update_memory(self, engine, job: Job, run: JobRun):
        worktree = self.config.local_path.parent.parent
        summary = None
        if engine is not None:
            try:
                messages = []
                prior = read_memory(worktree, job)
                if prior:
                    messages.append(
                        {'role': 'system',
                         'content': f'Previous run memory:\n{prior}'})
                messages += list(engine.current_session.messages)
                summary = engine._summarize(messages)
                if summary:
                    summary = str(summary).strip()
            except Exception:
                summary = None
        if not summary:
            summary = f'Run {run.started_at}: {run.status}.'
            if run.content:
                summary += f'\n{run.content}'
            elif run.reason:
                summary += f'\nError: {run.reason}'
            summary = summary[:1500]
        write_memory(worktree, job, summary)
        self._out(f'{job.name}: run memory updated')

    def _finish(self, job: Job, run: JobRun, finished: datetime) -> JobRun:
        job.last_run_at = run.started_at
        job.status = 'verified' if run.status == 'verified' else 'failed'
        if job.require_approval:
            job.status = 'waiting_approval'
            job.approval_pending = False
        if job.schedule.get('at'):
            job.enabled = False
            job.next_run_at = ''
        else:
            next_at = compute_next_run(job, finished)
            job.next_run_at = next_at.isoformat(timespec='seconds') if next_at else ''
        self.registry.save()
        verb = 'verified' if run.status == 'verified' else 'failed'
        if job.require_approval:
            verb += ' (next run waits for approval)'
        self._out(f'{job.name}: {verb} ({run.duration}s, '
                  f'{len(job.history)} run(s) recorded)')
        return run

    def tick(self, now: datetime | None = None):
        now = now or datetime.now(timezone.utc)
        due = []
        for job in self.registry.all():
            if not job.ready_to_run():
                continue
            try:
                next_at = parse_dt(job.next_run_at) if job.next_run_at else now
            except ValueError:
                next_at = now
            if next_at <= now:
                due.append(job)
        for job in due:
            self.run_job(job)

    def daemon(self, tick_seconds: float = 15.0):
        self._out('job scheduler started - press Ctrl-C to stop')
        try:
            while True:
                try:
                    self.tick()
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self._out(f'error in scheduler tick: {e}', error=True)
                time.sleep(max(1.0, float(tick_seconds)))
        except KeyboardInterrupt:
            self._out('job scheduler stopped')
        return 0
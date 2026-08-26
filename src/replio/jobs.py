import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

MIN_INTERVAL = 60
CRON_HORIZON_DAYS = 4 * 366 + 1


def parse_cron_field(field: str, lo: int, hi: int) -> set[int]:
    out: set[int] = set()
    for element in field.split(','):
        element = element.strip()
        if not element:
            raise ValueError(f'empty element in field "{field}"')
        step = 1
        base = element
        if '/' in element:
            base, _, step_str = element.partition('/')
            step = int(step_str)
            if step <= 0:
                raise ValueError(f'invalid step in "{element}"')
        if base == '*':
            values = range(lo, hi + 1)
        elif '-' in base:
            a, _, b = base.partition('-')
            values = range(int(a), int(b) + 1)
        elif base.isdigit():
            values = range(int(base), int(base) + 1)
        else:
            raise ValueError(f'invalid cron element "{element}"')
        for v in values:
            if not (lo <= v <= hi):
                raise ValueError(f'value {v} out of range {lo}-{hi}')
            if (v - lo) % step == 0:
                out.add(v)
    return out


def _parse_weekdays(field: str) -> set[int]:
    values = parse_cron_field(field, 0, 7)
    return {(v - 1) % 7 for v in values}


def next_run(cron_expr: str, after: datetime) -> datetime:
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(
            'cron expression must have exactly 5 fields: minute hour dom month dow')
    minutes = parse_cron_field(parts[0], 0, 59)
    hours = parse_cron_field(parts[1], 0, 23)
    doms = parse_cron_field(parts[2], 1, 31)
    months = parse_cron_field(parts[3], 1, 12)
    dows = _parse_weekdays(parts[4])
    tz = after.tzinfo
    start = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    day = start.date()
    for _ in range(CRON_HORIZON_DAYS):
        if day.month in months and day.day in doms and day.weekday() in dows:
            first = day == start.date()
            start_hour = start.hour if first else 0
            start_minute = start.minute if first else 0
            for h in sorted(hours):
                if h < start_hour:
                    continue
                minute_lo = start_minute if h == start_hour else 0
                for m in sorted(minutes):
                    if m >= minute_lo:
                        return datetime(day.year, day.month, day.day, h, m,
                                        tzinfo=tz)
        day += timedelta(days=1)
    raise ValueError('no matching cron time found within 4 years')


def parse_dt(value: str) -> datetime:
    text = value.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f'invalid datetime: {value}')
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _clamp_interval(value) -> int:
    try:
        interval = max(MIN_INTERVAL, int(value))
    except (TypeError, ValueError):
        interval = MIN_INTERVAL
    return interval


def compute_next_run(job: 'Job', after: datetime) -> datetime | None:
    schedule = job.schedule or {}
    if schedule.get('cron'):
        return next_run(str(schedule['cron']), after)
    if schedule.get('interval'):
        return after + timedelta(seconds=_clamp_interval(schedule['interval']))
    if schedule.get('at'):
        at = parse_dt(str(schedule['at']))
        return at if at > after else None
    return None


@dataclass
class JobRun:
    started_at: str = ''
    finished_at: str = ''
    status: str = ''
    reason: str = ''
    duration: float = 0.0
    session: str = ''
    attempt: int = 0

    def to_dict(self) -> dict:
        return {
            'started_at': self.started_at,
            'finished_at': self.finished_at,
            'status': self.status,
            'reason': self.reason,
            'duration': self.duration,
            'session': self.session,
            'attempt': self.attempt,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'JobRun':
        return cls(
            started_at=d.get('started_at', ''),
            finished_at=d.get('finished_at', ''),
            status=d.get('status', ''),
            reason=d.get('reason', ''),
            duration=d.get('duration', 0.0),
            session=d.get('session', ''),
            attempt=d.get('attempt', 0),
        )


@dataclass
class Job:
    name: str
    schedule: dict
    prompt: str = ''
    session: str = ''
    mode: str = ''
    provider: str = ''
    model: str = ''
    persona: str = ''
    system_prompt: str = ''
    tool_permission: dict = field(default_factory=dict)
    tools_deny: list = field(default_factory=list)
    retries: int = 3
    backoff: float = 60.0
    timeout: int = 0
    enabled: bool = True
    status: str = 'proposed'
    next_run_at: str = ''
    last_run_at: str = ''
    history: list = field(default_factory=list)

    def runnable(self) -> bool:
        return bool(self.enabled) and self.status in ('approved', 'verified', 'failed')

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'schedule': dict(self.schedule),
            'prompt': self.prompt,
            'session': self.session,
            'mode': self.mode,
            'provider': self.provider,
            'model': self.model,
            'persona': self.persona,
            'system_prompt': self.system_prompt,
            'tool_permission': dict(self.tool_permission),
            'tools_deny': list(self.tools_deny),
            'retries': self.retries,
            'backoff': self.backoff,
            'timeout': self.timeout,
            'enabled': self.enabled,
            'status': self.status,
            'next_run_at': self.next_run_at,
            'last_run_at': self.last_run_at,
            'history': [r.to_dict() for r in self.history],
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Job':
        return cls(
            name=d.get('name', ''),
            schedule=dict(d.get('schedule') or {}),
            prompt=d.get('prompt', ''),
            session=d.get('session', ''),
            mode=d.get('mode', ''),
            provider=d.get('provider', ''),
            model=d.get('model', ''),
            persona=d.get('persona', ''),
            system_prompt=d.get('system_prompt', ''),
            tool_permission=dict(d.get('tool_permission') or {}),
            tools_deny=list(d.get('tools_deny') or []),
            retries=d.get('retries', 3),
            backoff=d.get('backoff', 60.0),
            timeout=d.get('timeout', 0),
            enabled=d.get('enabled', True),
            status=d.get('status', 'proposed'),
            next_run_at=d.get('next_run_at', ''),
            last_run_at=d.get('last_run_at', ''),
            history=[JobRun.from_dict(r) for r in (d.get('history') or [])
                     if isinstance(r, dict)],
        )


class JobRegistry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._jobs: dict[str, Job] = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        raw = data.get('jobs', []) if isinstance(data, dict) else []
        for d in raw if isinstance(raw, list) else []:
            if isinstance(d, dict) and d.get('name'):
                job = Job.from_dict(d)
                self._jobs[job.name] = job

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps({'jobs': [j.to_dict() for j in self.all()]},
                                  indent=2))
        os.replace(tmp, self.path)

    def all(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.name)

    def find(self, name: str) -> Job | None:
        return self._jobs.get(name)

    def put(self, job: Job):
        self._jobs[job.name] = job
        self.save()

    def remove(self, name: str) -> bool:
        if name in self._jobs:
            del self._jobs[name]
            self.save()
            return True
        return False


def describe_schedule(job: Job) -> str:
    schedule = job.schedule or {}
    if schedule.get('cron'):
        return f"cron '{schedule['cron']}'"
    if schedule.get('interval'):
        return f'every {int(schedule["interval"])}s'
    if schedule.get('at'):
        return f'at {schedule["at"]}'
    return 'unscheduled'


def validate_schedule(schedule: dict):
    if not isinstance(schedule, dict):
        raise ValueError('schedule must be a mapping')
    if schedule.get('cron'):
        next_run(str(schedule['cron']), datetime.now(timezone.utc))
    elif schedule.get('at'):
        parse_dt(str(schedule['at']))
    elif not schedule.get('interval'):
        raise ValueError('schedule needs one of: cron, interval, at')


def publish(registry: JobRegistry, job: Job, print=print):
    now = datetime.now(timezone.utc)
    next_at = compute_next_run(job, now)
    job.next_run_at = next_at.isoformat(timespec='seconds') if next_at else ''
    registry.put(job)
    gate = ('approved - runs on schedule' if job.status == 'approved'
            else 'proposed - approve it to activate '
                 '(`replio jobs approve <name>` or /jobs approve <name>)')
    print(f'Added job: {job.name} [{job.status}]')
    print(f'  schedule: {describe_schedule(job)}')
    print(f'  next run: {job.next_run_at or "-"}')
    print(f'  status:   {gate}')


def _fmt_dt(value: str) -> str:
    return value or '-'


def render_list(registry: JobRegistry, print=print):
    jobs = registry.all()
    if not jobs:
        print('  (no jobs configured)')
        print('  Add one with: replio jobs add <name> --cron "0 2 * * *" --prompt "..."')
        return
    print(f'{len(jobs)} jobs:')
    for job in jobs:
        schedule = describe_schedule(job)
        next_at = _fmt_dt(job.next_run_at)
        last = _fmt_dt(job.last_run_at)
        gate = 'runnable' if job.runnable() else (
            'proposed' if job.status == 'proposed' else 'disabled')
        print(f'  {job.name:<20} {schedule:<28} {job.status:<8} '
              f'{gate:<9} next: {next_at:<27} last: {last}')


def render_show(registry: JobRegistry, name: str, print=print) -> bool:
    job = registry.find(name)
    if job is None:
        print(f'  Job not found: {name}')
        return False
    print(f'{job.name} [{job.status}] {"enabled" if job.enabled else "disabled"}')
    print(f'  schedule:   {describe_schedule(job)}')
    print(f'  prompt:     {job.prompt}')
    print(f'  session:    {job.session or f"job.{job.name}"}')
    if job.mode:
        print(f'  mode:       {job.mode}')
    if job.persona:
        print(f'  persona:    {job.persona}')
    if job.provider:
        print(f'  provider:   {job.provider}')
    if job.model:
        print(f'  model:      {job.model}')
    if job.tool_permission:
        print('  tool_permission: ' + json.dumps(job.tool_permission))
    if job.tools_deny:
        print(f'  tools.deny: {", ".join(job.tools_deny)}')
    if job.system_prompt:
        print(f'  system_prompt: {job.system_prompt[:80]}')
    print(f'  durability: retries={job.retries} backoff={job.backoff}s '
          f'timeout={job.timeout if job.timeout else "none"}s')
    print(f'  next run:   {_fmt_dt(job.next_run_at)}')
    print(f'  last run:   {_fmt_dt(job.last_run_at)}')
    print(f'  history:    {len(job.history)} run(s)')
    if job.history:
        for run in reversed(job.history):
            span = f'{_fmt_dt(run.started_at)} -> {_fmt_dt(run.finished_at)}'
            detail = run.reason or ''
            print(f'    {run.status:<8} attempt {run.attempt}: {span} '
                  f'({run.duration}s){"  " + detail if detail else ""}')
            if run.session:
                print(f'      session: {run.session}')
    return True
import pickle
import csv
import json
import logging
import functools
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


# ─────────────────────────────────────────────
#  ЛОГУВАННЯ У ФАЙЛ (декоратор використовує це)
# ─────────────────────────────────────────────
logging.basicConfig(
    filename="history.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)


# ─────────────────────────────────────────────
#  7. ДЕКОРАТОР @log_action
# ─────────────────────────────────────────────
def log_action(action_name: str):
    """Декоратор: автоматично логує кожну дію у history.log"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            logging.info(f"[{action_name}] args={args[1:]}")
            return result
        return wrapper
    return decorator


# ─────────────────────────────────────────────
#  ENUM
# ─────────────────────────────────────────────
class Status(Enum):
    TODO       = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE       = "DONE"
    BLOCKED    = "BLOCKED"


# ─────────────────────────────────────────────
#  @DATACLASS — зберігання налаштувань (ТЗ п.1)
# ─────────────────────────────────────────────
@dataclass
class AppConfig:
    project_name:      str  = "Kanban CLI"
    max_tasks_per_page: int = 3
    author:            str  = "anonymous"
    version:           str  = "1.0.0"
    log_file:          str  = "history.log"
    tags:              list = field(default_factory=list)

    def __str__(self):
        return (
            f"AppConfig(project='{self.project_name}', "
            f"page_size={self.max_tasks_per_page}, "
            f"author='{self.author}', v{self.version})"
        )

    def __repr__(self):
        return (
            f"AppConfig(project_name={self.project_name!r}, "
            f"max_tasks_per_page={self.max_tasks_per_page!r}, "
            f"author={self.author!r}, version={self.version!r})"
        )


# ─────────────────────────────────────────────
#  СУТНОСТІ  (інкапсуляція + магічні методи)
# ─────────────────────────────────────────────
class Task:
    def __init__(
        self,
        title: str,
        priority: int,
        status: Status = Status.TODO,
        assignee: Optional[str] = None,
        deadline: Optional[datetime] = None,
    ):
        # Інкапсуляція: захищені атрибути (ТЗ п.2)
        self._title    = None
        self._priority = None
        # Використовуємо сетери з валідацією
        self.title    = title
        self.priority = priority
        self.status   = status
        self.assignee = assignee
        self.deadline = deadline
        self.created_at = datetime.now()

    # ── @property / @setter з валідацією (ТЗ п.2) ──
    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        if not value or not value.strip():
            raise ValueError("Назва завдання не може бути порожньою!")
        self._title = value.strip()

    @property
    def priority(self) -> int:
        return self._priority

    @priority.setter
    def priority(self, value: int):
        if not isinstance(value, int) or not (1 <= value <= 10):
            raise ValueError("Пріоритет має бути цілим числом від 1 до 10!")
        self._priority = value

    # ── Оператори порівняння __lt__ (ТЗ п.6) ──────
    def __lt__(self, other: "Task") -> bool:
        """Порівняння за пріоритетом (для сортування)."""
        return self._priority < other._priority

    def __le__(self, other: "Task") -> bool:
        return self._priority <= other._priority

    def __gt__(self, other: "Task") -> bool:
        return self._priority > other._priority

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return NotImplemented
        return self._priority == other._priority

    # ── __str__ / __repr__ ────────────────────────
    def __str__(self):
        deadline_str = ""
        if self.deadline:
            overdue = self.deadline < datetime.now() and self.status != Status.DONE
            mark = " ⚠ ПРОСТРОЧЕНО" if overdue else f" (до {self.deadline.strftime('%d.%m.%Y')})"
            deadline_str = mark
        assignee_str = f" → {self.assignee}" if self.assignee else ""
        return (
            f"[{self.status.value:<11}] "
            f"P{self._priority} | "
            f"{self.__class__.__name__:<14} "
            f"'{self._title}'"
            f"{assignee_str}"
            f"{deadline_str}"
        )

    def __repr__(self):
        return f"{self.__class__.__name__}('{self._title}', priority={self._priority}, {self.status.name})"

    # ── Поліморфізм: розрахунок складності ────
    def calculate_complexity(self) -> float:
        """Базовий розрахунок складності завдання."""
        return round(self._priority * 2.5, 2)

class BugReport(Task):
    def __str__(self):
        return f"[BUG] {super().__str__()}"

    def calculate_complexity(self) -> float:
        """Баги складніші — підвищений коефіцієнт 1.5."""
        return round(self._priority * 2.5 * 1.5, 2)

class FeatureRequest(Task):
    def __str__(self):
        return f"[FEATURE] {super().__str__()}"

    def calculate_complexity(self) -> float:
        """Фічі менш критичні — коефіцієнт 1.2."""
        return round(self._priority * 2.5 * 1.2, 2)
# ─────────────────────────────────────────────
#  1. ФУНКТОР
# ─────────────────────────────────────────────
class TaskComplexityAnalyzer:
    def __init__(self, base_multiplier: float):
        self.base_multiplier  = base_multiplier
        self.analyzed_count   = 0
        self.total_complexity = 0.0

    def __call__(self, task: Task) -> float:
        self.analyzed_count += 1
        complexity = task.calculate_complexity()  # поліморфний виклик
        self.total_complexity += complexity
        return complexity


# ─────────────────────────────────────────────
#  2. ВЛАСНИЙ ІТЕРАТОР
# ─────────────────────────────────────────────
class PriorityTaskIterator:
    def __init__(self, tasks, status_filter=None):
        filtered = [t for t in tasks if status_filter is None or t.status == status_filter]
        self._sorted_tasks = sorted(filtered, key=lambda t: t.priority, reverse=True)
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < len(self._sorted_tasks):
            task = self._sorted_tasks[self.index]
            self.index += 1
            return task
        raise StopIteration


# ─────────────────────────────────────────────
#  1. МЕНЕДЖЕР КОНТЕКСТУ (вимога курсової)
# ─────────────────────────────────────────────
class StatusChangeContext:
    """
    Контекстний менеджер для зміни статусу завдання.
    Логує: хто, коли, з якого на який статус.
    """
    def __init__(self, task: Task, new_status: Status, user: str = "anonymous"):
        self.task       = task
        self.new_status = new_status
        self.user       = user
        self.old_status = task.status

    def __enter__(self):
        self.task.status = self.new_status
        return self.task

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            msg = (
                f"[STATUS CHANGE] user='{self.user}' | "
                f"task='{self.task.title}' | "
                f"{self.old_status.value} → {self.new_status.value}"
            )
            logging.info(msg)
            print(f"  ✔ Залоговано: {self.old_status.value} → {self.new_status.value} (by {self.user})")
        else:
            # Відкат при помилці
            self.task.status = self.old_status
            print(f"  ✖ Помилка! Статус відкочено до {self.old_status.value}")
        return False   # не пригнічуємо виключення


# ─────────────────────────────────────────────
#  3. МЕНЕДЖЕР ЗАВДАНЬ
# ─────────────────────────────────────────────
class TaskManager:
    def __init__(self):
        self._tasks: List[Task] = []
        self.analyzer = TaskComplexityAnalyzer(base_multiplier=2.5)
        self.config   = AppConfig()   # використовуємо @dataclass

    # 7. Декоратор логування
    @log_action("ADD_TASK")
    def add_task(self, task: Task):
        self._tasks.append(task)

    def get_all_tasks(self) -> List[Task]:
        return self._tasks

    # ── __getitem__ (ТЗ п.6) ──────────────────
    def __getitem__(self, index: int) -> Task:
        """Пошук завдання за індексом: manager[0]"""
        if not (0 <= index < len(self._tasks)):
            raise IndexError(f"Завдання з індексом {index} не існує!")
        return self._tasks[index]

    def __len__(self) -> int:
        return len(self._tasks)

    def get_all_tasks(self) -> List[Task]:
        return self._tasks

    def generate_tasks_by_pages(self, page_size: int):
        for i in range(0, len(self._tasks), page_size):
            yield self._tasks[i : i + page_size]

    def get_priority_iterator(self, status_filter: Optional[Status] = None):
        return PriorityTaskIterator(self._tasks, status_filter)

    # ── 1. Менеджер контексту ──────────────────
    def change_status(self, task: Task, new_status: Status, user: str = "anonymous"):
        """Повертає контекстний менеджер для зміни статусу."""
        return StatusChangeContext(task, new_status, user)

    # ── 4. Зміна статусу через меню ───────────
    @log_action("STATUS_CHANGE")
    def set_status(self, task_index: int, new_status: Status, user: str = "anonymous"):
        task = self._tasks[task_index]
        with self.change_status(task, new_status, user):
            pass   # вся логіка всередині __enter__ / __exit__

    # ── 5. Пошук і фільтрація ─────────────────
    def search(self, keyword: str) -> List[Task]:
        kw = keyword.lower()
        return [t for t in self._tasks if kw in t.title.lower()]

    def filter_by_status(self, status: Status) -> List[Task]:
        return [t for t in self._tasks if t.status == status]

    def filter_by_assignee(self, assignee: str) -> List[Task]:   # 8
        return [t for t in self._tasks if t.assignee == assignee]

    # ── 6. Статистика / дашборд ───────────────
    def get_statistics(self) -> dict:
        total = len(self._tasks)
        by_status = {s: 0 for s in Status}
        for t in self._tasks:
            by_status[t.status] += 1

        complexities = [self.analyzer(t) for t in self._tasks]
        avg_complexity = sum(complexities) / total if total else 0

        top3 = sorted(self._tasks, key=lambda t: t.priority, reverse=True)[:3]

        # 9. Прострочені
        now = datetime.now()
        overdue = [
            t for t in self._tasks
            if t.deadline and t.deadline < now and t.status != Status.DONE
        ]

        return {
            "total":         total,
            "by_status":     by_status,
            "avg_complexity": avg_complexity,
            "top3":          top3,
            "overdue":       overdue,
        }

    # ── 9. Авто-блокування прострочених ───────
    @log_action("AUTO_BLOCK_OVERDUE")
    def auto_block_overdue(self, user: str = "system"):
        now = datetime.now()
        count = 0
        for task in self._tasks:
            if (
                task.deadline
                and task.deadline < now
                and task.status not in (Status.DONE, Status.BLOCKED)
            ):
                with self.change_status(task, Status.BLOCKED, user=user):
                    pass
                count += 1
        return count

    # ── JSON config ───────────────────────────
    def load_config(self, filepath: str = "config.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.config = AppConfig(
                project_name       = data.get("project_name", "Kanban CLI"),
                max_tasks_per_page = data.get("max_tasks_per_page", 3),
                author             = data.get("author", "anonymous"),
                version            = data.get("version", "1.0.0"),
                log_file           = data.get("log_file", "history.log"),
                tags               = data.get("tags", []),
            )
            print(f"[Config] {self.config}")
        except FileNotFoundError:
            self.config = AppConfig()
            print("[Config] config.json не знайдено — використано значення за замовчуванням.")

    # ── Pickle ────────────────────────────────
    def save_state(self, filepath: str = "tasks.pkl"):
        with open(filepath, "wb") as f:
            pickle.dump(self._tasks, f)
        print(f"[Pickle] Стан збережено ({len(self._tasks)} завдань) → '{filepath}'")

    def load_state(self, filepath: str = "tasks.pkl"):
        try:
            with open(filepath, "rb") as f:
                self._tasks = pickle.load(f)
            print(f"[Pickle] Відновлено {len(self._tasks)} завдань")
        except FileNotFoundError:
            print(f"[Pickle] Файл '{filepath}' не знайдено — старт із порожнього списку.")

    # ── CSV ───────────────────────────────────
    @log_action("EXPORT_CSV")
    def export_report(self, filepath: str = "tasks_report.csv"):
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([
                "Назва завдання", "Тип", "Пріоритет", "Статус",
                "Складність", "Виконавець", "Дедлайн", "Створено"
            ])
            for task in self._tasks:
                complexity = task.calculate_complexity()
                writer.writerow([
                    task.title,
                    task.__class__.__name__,
                    task.priority,
                    task.status.value,
                    f"{complexity:.1f}",
                    task.assignee or "—",
                    task.deadline.strftime("%d.%m.%Y") if task.deadline else "—",
                    task.created_at.strftime("%d.%m.%Y %H:%M"),
                ])
        print(f"[CSV] Звіт експортовано → '{filepath}'")
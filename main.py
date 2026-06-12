import sys
from datetime import datetime
from task_manager import TaskManager, BugReport, FeatureRequest, Status
 
 
# ─────────────────────────────────────────────
#  ДОПОМІЖНІ ФУНКЦІЇ ВИВОДУ
# ─────────────────────────────────────────────
def divider(char="─", width=50):
    print(char * width)
 
def header(title: str):
    print()
    divider("═")
    print(f"  {title}")
    divider("═")
 
def show_menu():
    header("ГОЛОВНЕ МЕНЮ: KANBAN CLI")
    print("  1. Показати всі завдання (сторінками)")
    print("  2. Створити BugReport     (Помилка)")
    print("  3. Створити FeatureRequest (Нова фіча)")
    print("  4. Змінити статус завдання")       # NEW
    print("  5. Пошук / фільтрація")            # NEW
    print("  6. Статистика (дашборд)")           # NEW
    print("  7. Мої завдання (за виконавцем)")  # NEW
    print("  8. Перевірити прострочені")         # NEW
    print("  9. Зберегти стан (Pickle)")
    print(" 10. Експортувати звіт (CSV)")
    print("  0. Вихід")
    divider()
 
# ─────────────────────────────────────────────
#  10. ІНТЕРАКТИВНИЙ ВИБІР СТАТУСУ
# ─────────────────────────────────────────────
def choose_status() -> Status:
    statuses = list(Status)
    print("\n  Оберіть статус:")
    for i, s in enumerate(statuses, 1):
        print(f"    {i}. {s.value}")
    while True:
        try:
            idx = int(input("  Номер статусу: ")) - 1
            if 0 <= idx < len(statuses):
                return statuses[idx]
            print("  Невірний номер!")
        except ValueError:
            print("  Введіть цифру!")
 
# ─────────────────────────────────────────────
#  ВИБІР ЗАВДАННЯ ЗІ СПИСКУ
# ─────────────────────────────────────────────
def choose_task(tasks) -> int:
    """Показує пронумерований список і повертає індекс у глобальному списку."""
    for i, task in enumerate(tasks):
        print(f"  {i+1}. {task}")
    while True:
        try:
            idx = int(input("  Номер завдання: ")) - 1
            if 0 <= idx < len(tasks):
                return idx
            print("  Невірний номер!")
        except ValueError:
            print("  Введіть цифру!")
 
# ─────────────────────────────────────────────
#  ЗЧИТУВАННЯ ДЕДЛАЙНУ (необов'язково)
# ─────────────────────────────────────────────
def read_deadline() -> datetime | None:
    raw = input("  Дедлайн (дд.мм.рррр) або Enter щоб пропустити: ").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%d.%m.%Y")
    except ValueError:
        print("  Невірний формат дати — дедлайн не встановлено.")
        return None
 
 
# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    manager = TaskManager()
 
    print("\n  Ініціалізація Kanban CLI...")
    manager.load_config("config.json")
    manager.load_state("tasks.pkl")
 
    # При старті автоматично перевіряємо прострочені
    blocked = manager.auto_block_overdue(user="system")
    if blocked:
        print(f"  ⚠  Автоматично заблоковано {blocked} прострочених завдань.")
 
    while True:
        show_menu()
        try:
            choice = input("  Оберіть дію (0-10): ").strip()
 
            # ── 1. Всі завдання (сторінками) ──────────────
            match choice:
                case "1":
                    header("Список завдань")
                    page_size = manager.config.max_tasks_per_page
                    pages = list(manager.generate_tasks_by_pages(page_size))
                    if not pages:
                        print("  [Інфо] Список завдань порожній.")
                    else:
                        for page_num, page in enumerate(pages, 1):
                            print(f"\n  ─── Сторінка {page_num}/{len(pages)} ───")
                            for task in page:
                                print(f"    {task}")
                            if page_num < len(pages):
                                input("\n  Enter → наступна сторінка...")
 
                # ── 2. Створити BugReport ──────────────────
                case "2":
                    header("Новий BugReport")
                    title    = input("  Назва помилки: ").strip()
                    if not title:
                        raise ValueError("Назва не може бути порожньою!")
                    priority = int(input("  Пріоритет (1-10): "))
                    assignee = input("  Виконавець (або Enter): ").strip() or None
                    deadline = read_deadline()
                    manager.add_task(BugReport(title, priority, Status.TODO, assignee, deadline))
                    print(f"\n  ✔ BugReport '{title}' додано!")
 
                # ── 3. Створити FeatureRequest ─────────────
                case "3":
                    header("Новий FeatureRequest")
                    title    = input("  Опис фічі: ").strip()
                    if not title:
                        raise ValueError("Опис не може бути порожнім!")
                    priority = int(input("  Пріоритет (1-10): "))
                    assignee = input("  Виконавець (або Enter): ").strip() or None
                    deadline = read_deadline()
                    manager.add_task(FeatureRequest(title, priority, Status.TODO, assignee, deadline))
                    print(f"\n  ✔ FeatureRequest '{title}' додано!")
 
                # ── 4. Змінити статус ──────────────────────
                case "4":
                    header("Зміна статусу завдання")
                    all_tasks = manager.get_all_tasks()
                    if not all_tasks:
                        print("  Немає завдань!")
                    else:
                        task_idx = choose_task(all_tasks)
                        new_status = choose_status()
                        user = input("  Ваше ім'я: ").strip() or "anonymous"
                        manager.set_status(task_idx, new_status, user)
 
                # ── 5. Пошук і фільтрація ──────────────────
                case "5":
                    header("Пошук / Фільтрація")
                    print("  a. Пошук за ключовим словом")
                    print("  b. Фільтр за статусом")
                    sub = input("  Оберіть (a/b): ").strip().lower()
                    if sub == "a":
                        kw = input("  Ключове слово: ").strip()
                        results = manager.search(kw)
                        if results:
                            print(f"\n  Знайдено {len(results)}:")
                            for t in results:
                                print(f"    {t}")
                        else:
                            print("  Нічого не знайдено.")
                    elif sub == "b":
                        status = choose_status()
                        results = manager.filter_by_status(status)
                        print(f"\n  Завдань зі статусом {status.value}: {len(results)}")
                        for t in results:
                            print(f"    {t}")
 
                # ── 6. Статистика ──────────────────────────
                case "6":
                    header("Статистика / Дашборд")
                    stats = manager.get_statistics()
                    print(f"  Всього завдань : {stats['total']}")
                    print(f"  Середня складність: {stats['avg_complexity']:.1f}")
                    print()
                    print("  По статусах:")
                    for status, count in stats["by_status"].items():
                        bar = "█" * count
                        print(f"    {status.value:<12} {bar} ({count})")
                    print()
                    print("  Топ-3 за пріоритетом:")
                    for t in stats["top3"]:
                        print(f"    {t}")
                    if stats["overdue"]:
                        print(f"\n  ⚠  Прострочені ({len(stats['overdue'])}):")
                        for t in stats["overdue"]:
                            print(f"    {t}")
 
                # ── 7. Мої завдання ────────────────────────
                case "7":
                    header("Завдання за виконавцем")
                    assignee = input("  Ім'я виконавця: ").strip()
                    results  = manager.filter_by_assignee(assignee)
                    if results:
                        print(f"\n  Завдань у {assignee}: {len(results)}")
                        for t in results:
                            print(f"    {t}")
                    else:
                        print(f"  Завдань для '{assignee}' не знайдено.")
 
                # ── 8. Перевірити прострочені ──────────────
                case "8":
                    header("Перевірка прострочених")
                    user = input("  Ваше ім'я (для логу): ").strip() or "system"
                    blocked = manager.auto_block_overdue(user=user)
    
                    overdue_list = manager.filter_by_status(Status.BLOCKED)
                    if overdue_list:
                        print(f"\n  Список прострочених завдань ({len(overdue_list)}):")
                        for task in overdue_list:
                            print(f"    {task}")
                    else:
                        print("\n  ✔ Прострочених завдань немає.")
    
                    if blocked:
                        print(f"\n  ⚠  Щойно заблоковано нових: {blocked}")
 
                # ── 9. Зберегти ────────────────────────────
                case "9":
                    manager.save_state("tasks.pkl")
 
                # ── 10. CSV ────────────────────────────────
                case "10":
                    manager.export_report("tasks_report.csv")
 
                # ── 0. Вихід ───────────────────────────────
                case "0":
                    print("\n  Збереження та завершення...")
                    manager.save_state("tasks.pkl")
                    sys.exit(0)
 
                case _:
                    print("\n  [Увага] Невідома команда! Введіть цифру від 0 до 10.")
 
        except ValueError as e:
            print(f"\n  [Помилка введення]: {e}")
            print("  Система не впала. Спробуйте ще раз.")
        except Exception as e:
            print(f"\n  [Критична помилка]: {e}")
 
#!/usr/bin/env python3
"""
AI Website Testing Agent — Demo Runner

Запускает демонстрацию агентской системы на подобранных тест-кейсах,
показывает прогресс в реальном времени и открывает Allure-отчёт.

Использование:
  python demo.py             # Полная демонстрация (все сайты)
  python demo.py --quick     # Быстрая демо (5 кейсов, ~15 мин)
  python demo.py --site sd   # Только SauceDemo
  python demo.py --site ae   # Только AutomationExercise
  python demo.py --site ti   # Только The-Internet
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Curated demo suites
# ---------------------------------------------------------------------------

_SD = [  # SauceDemo — интернет-магазин
    "test_cases/saucedemo/tc_01_login_valid.yaml",
    "test_cases/saucedemo/tc_02_login_invalid.yaml",
    "test_cases/saucedemo/tc_08_locked_out_user.yaml",
    "test_cases/saucedemo/tc_03_add_to_cart.yaml",
    "test_cases/saucedemo/tc_07_sort_products.yaml",
    "test_cases/saucedemo/tc_04_checkout_flow.yaml",
    "test_cases/saucedemo/tc_05_problem_user_images.yaml",
    "test_cases/saucedemo/tc_06_problem_user_sort.yaml",
]

_TI = [  # The Internet — учебный сайт Heroku
    "test_cases/the_internet/tc_05_form_auth.yaml",
    "test_cases/the_internet/tc_06_dynamic_loading.yaml",
]

_AE = [  # AutomationExercise — полноценный e-commerce
    "test_cases/automationexercise/tc_ae_02_login_valid.yaml",
    "test_cases/automationexercise/tc_ae_03_login_invalid.yaml",
    "test_cases/automationexercise/tc_ae_04_search_product.yaml",
    "test_cases/automationexercise/tc_ae_05_add_to_cart.yaml",
    "test_cases/automationexercise/tc_ae_07_category_navigation.yaml",
    "test_cases/automationexercise/tc_ae_10_product_detail_page.yaml",
]

_QUICK = [
    "test_cases/saucedemo/tc_01_login_valid.yaml",
    "test_cases/saucedemo/tc_02_login_invalid.yaml",
    "test_cases/saucedemo/tc_04_checkout_flow.yaml",
    "test_cases/the_internet/tc_05_form_auth.yaml",
    "test_cases/automationexercise/tc_ae_04_search_product.yaml",
]

_ALL = _SD + _TI + _AE

ALLURE_BAT = r"C:\Program Files\allure-2.42.1\bin\allure.bat"
ALLURE_RESULTS = "allure-results"

# ---------------------------------------------------------------------------
# ANSI colours (stripped on Windows if not supported)
# ---------------------------------------------------------------------------

def _supports_ansi() -> bool:
    return sys.platform != "win32" or os.getenv("TERM") == "xterm"


_USE_ANSI = _supports_ansi()

BOLD  = "\033[1m"  if _USE_ANSI else ""
RESET = "\033[0m"  if _USE_ANSI else ""
CYAN  = "\033[96m" if _USE_ANSI else ""
GREEN = "\033[92m" if _USE_ANSI else ""
RED   = "\033[91m" if _USE_ANSI else ""
YELLOW= "\033[93m" if _USE_ANSI else ""
DIM   = "\033[2m"  if _USE_ANSI else ""

W = 68  # banner width


def hr(char: str = "=") -> str:
    return char * W


def banner() -> None:
    print()
    print(hr())
    print(f"{'AI WEBSITE TESTING AGENT':^{W}}")
    print(f"{'LangGraph + Playwright + Ollama + Allure':^{W}}")
    print(hr())
    print()
    print("  Агентская система, которая:")
    print("  - Читает тест-кейсы на РУССКОМ естественном языке")
    print("  - Самостоятельно управляет браузером через Playwright")
    print("  - Находит баги и генерирует pytest-тесты")
    print("  - Публикует отчёт в Allure с рассуждениями агента")
    print()


def section(title: str) -> None:
    print()
    print(hr("-"))
    print(f"  {BOLD}{title}{RESET}")
    print(hr("-"))


def site_header(label: str, url: str, count: int) -> None:
    print()
    print(f"  {CYAN}{BOLD}[{label}]{RESET}  {url}")
    print(f"  {DIM}Тест-кейсов: {count}{RESET}")


def _tc_label(path: str) -> str:
    name = Path(path).stem
    return name.replace("_", " ").upper()


def run_suite(
    label: str,
    cases: list[str],
    headless: bool = False,
) -> list[dict]:
    results: list[dict] = []
    for i, tc_path in enumerate(cases, 1):
        tc_label = _tc_label(tc_path)
        pad = f"[{i}/{len(cases)}]"
        print(f"\n  {DIM}{pad}{RESET} {tc_label}")

        cmd = [sys.executable, "run_tests.py", tc_path]
        if headless:
            cmd.append("--headless")

        t0 = time.time()
        proc = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
        )
        elapsed = time.time() - t0
        ok = proc.returncode == 0

        icon = f"{GREEN}OK{RESET}" if ok else f"{YELLOW}??{RESET}"
        print(f"  {icon}  {elapsed:.0f}s")
        results.append({"label": tc_label, "ok": ok, "elapsed": elapsed})

    return results


def print_summary(all_results: list[dict], total_elapsed: float) -> None:
    section("ИТОГОВАЯ СВОДКА ДЕМОНСТРАЦИИ")
    passed = sum(1 for r in all_results if r["ok"])
    failed = len(all_results) - passed

    for r in all_results:
        icon = f"{GREEN}+{RESET}" if r["ok"] else f"{RED}-{RESET}"
        print(f"  [{icon}] {r['label'][:55]:<55}  {r['elapsed']:.0f}s")

    print()
    print(f"  Всего тестов  : {len(all_results)}")
    print(f"  Выполнено     : {GREEN}{passed}{RESET}")
    if failed:
        print(f"  С ошибками    : {RED}{failed}{RESET}")
    mins = int(total_elapsed // 60)
    secs = int(total_elapsed % 60)
    print(f"  Общее время   : {mins}m {secs}s")
    print()


def open_allure(interactive: bool = True) -> None:
    section("ОТКРЫТИЕ ALLURE-ОТЧЁТА")

    results_dir = Path(ALLURE_RESULTS)
    if not results_dir.exists() or not any(results_dir.iterdir()):
        print(f"  {YELLOW}Папка {ALLURE_RESULTS}/ пуста — отчёт не создавался{RESET}")
        return

    allure_bat = Path(ALLURE_BAT)
    if not allure_bat.exists():
        print(f"  {YELLOW}Allure не найден по пути:{RESET}")
        print(f"    {ALLURE_BAT}")
        print()
        print("  Запустите вручную:")
        print(f'  & "{ALLURE_BAT}" serve {ALLURE_RESULTS}')
        return

    print(f"  Запуск Allure-сервера...")
    print(f"  {DIM}Папка с результатами: {ALLURE_RESULTS}/{RESET}")
    print()
    print("  Браузер откроется автоматически.")
    print("  Нажмите Ctrl+C, чтобы остановить сервер.")
    print()

    if not interactive:
        print(f"  (Неинтерактивный режим — сервер не запущен)")
        print(f'  Запустите: & "{ALLURE_BAT}" serve {ALLURE_RESULTS}')
        return

    try:
        subprocess.run([str(allure_bat), "serve", ALLURE_RESULTS])
    except KeyboardInterrupt:
        print("\n  Allure-сервер остановлен.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo runner for AI Website Testing Agent"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick demo: 5 curated test cases (~15 min)",
    )
    parser.add_argument(
        "--site",
        choices=["sd", "ae", "ti"],
        help="Run only one site: sd=SauceDemo, ae=AutomationExercise, ti=The-Internet",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no window)",
    )
    parser.add_argument(
        "--no-allure",
        action="store_true",
        help="Skip opening Allure report at the end",
    )
    args = parser.parse_args()

    banner()

    # Select suite
    if args.quick:
        suite = _QUICK
        suite_name = "БЫСТРАЯ ДЕМОНСТРАЦИЯ"
        desc = "5 тест-кейсов (~15 мин)"
    elif args.site == "sd":
        suite = _SD
        suite_name = "SAUCEDEMO"
        desc = "Интернет-магазин"
    elif args.site == "ae":
        suite = _AE
        suite_name = "AUTOMATIONEXERCISE"
        desc = "E-commerce платформа"
    elif args.site == "ti":
        suite = _TI
        suite_name = "THE INTERNET (HEROKU)"
        desc = "Учебный сайт с динамическим контентом"
    else:
        suite = _ALL
        suite_name = "ПОЛНАЯ ДЕМОНСТРАЦИЯ"
        desc = f"{len(_ALL)} тест-кейсов на 3 сайтах"

    section(f"ПЛАН ДЕМОНСТРАЦИИ: {suite_name}")
    print(f"  {desc}")
    print(f"  Режим браузера: {'headless' if args.headless else 'видимый (с окном браузера)'}")
    print()
    for i, tc in enumerate(suite, 1):
        print(f"  {i:2}. {_tc_label(tc)}")
    print()
    print("  Запуск через 3 секунды...")
    time.sleep(3)

    # Run
    t_start = time.time()
    all_results: list[dict] = []

    if args.quick or args.site:
        # flat suite
        all_results = run_suite(suite_name, suite, headless=args.headless)
    else:
        # grouped by site
        site_header("SAUCEDEMO", "https://www.saucedemo.com", len(_SD))
        all_results += run_suite("SauceDemo", _SD, headless=args.headless)

        site_header("THE INTERNET", "https://the-internet.herokuapp.com", len(_TI))
        all_results += run_suite("The Internet", _TI, headless=args.headless)

        site_header("AUTOMATIONEXERCISE", "https://automationexercise.com", len(_AE))
        all_results += run_suite("AutomationExercise", _AE, headless=args.headless)

    total_elapsed = time.time() - t_start
    print_summary(all_results, total_elapsed)

    if not args.no_allure:
        open_allure(interactive=True)
    else:
        print()
        print(f"  Результаты сохранены в: {ALLURE_RESULTS}/")
        print(f'  Открыть отчёт: & "{ALLURE_BAT}" serve {ALLURE_RESULTS}')


if __name__ == "__main__":
    main()

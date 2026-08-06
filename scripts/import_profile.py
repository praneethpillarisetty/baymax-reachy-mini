from baymax.cli import main

raise SystemExit(main(["import", *__import__("sys").argv[1:]]))

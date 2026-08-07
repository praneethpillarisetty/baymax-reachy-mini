from baymax.cli import main

raise SystemExit(main(["export", *__import__("sys").argv[1:]]))

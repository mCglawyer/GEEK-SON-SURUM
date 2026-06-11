#!/usr/bin/env python
"""Django'nun komut satırı yardımcı aracı."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django içe aktarılamadı. Sanal ortamın aktif ve Django'nun "
            "kurulu olduğundan emin olun."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

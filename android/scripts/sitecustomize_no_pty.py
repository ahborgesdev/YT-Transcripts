"""Fuerza a `sh` a usar pipes en vez de PTY cuando no hay PTY disponible.

python-for-android ejecuta comandos con la librería `sh`, que por defecto
abre un pseudo-terminal para stdout (`_tty_out=True`). En entornos sin PTY
(contenedores, CI, sandboxes) `pty.openpty()` falla con
"out of pty devices" y la compilación se detiene.

`build.sh` copia este módulo a site-packages y lo activa con un `.pth` sólo
si `pty.openpty()` no funciona. En un Mac normal no se instala.
"""

try:
    import sh
except ImportError:  # sh aún no instalado en el intérprete actual
    pass
else:
    if not getattr(sh, "_buscador_no_pty_patch", False):
        _original_call = sh.Command.__call__

        def _call_without_pty(self, *args, **kwargs):
            kwargs.setdefault("_tty_in", False)
            kwargs.setdefault("_tty_out", False)
            return _original_call(self, *args, **kwargs)

        sh.Command.__call__ = _call_without_pty
        sh._buscador_no_pty_patch = True

from functools import wraps
from flask import session, flash, redirect

def requer_tipo(*tipos_permitidos):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tipo = session.get('tipo')
            print(f"DEBUG requer_tipo: sessão tipo='{tipo}', permitido={tipos_permitidos}")
            if tipo not in tipos_permitidos:
                flash("Acesso negado: você não tem permissão para isso.", "erro")
                return redirect('/home')  # ou outra rota de acesso negado
            return func(*args, **kwargs)
        return wrapper
    return decorator

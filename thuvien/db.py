from django.db import connection


def dictfetchall(cursor):
    if cursor.description is None:
        return []
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def run_select(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return dictfetchall(cursor)


def run_scalar_function(sql_expr, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql_expr, params or [])
        row = cursor.fetchone()
        return row[0] if row else None


def call_procedure(proc_name, params=None):
    params = params or []
    placeholders = ", ".join(["%s"] * len(params))
    sql = f"CALL {proc_name}({placeholders})"
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = []
            has_more = True
            while has_more:
                if cursor.description:
                    rows = dictfetchall(cursor)
                try:
                    has_more = cursor.nextset()
                except Exception:
                    has_more = False
                if has_more is None:
                    has_more = False
            return {"ok": True, "rows": rows}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

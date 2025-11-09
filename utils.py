import os
import tempfile
import matplotlib.pyplot as plt
from database import db_connect


def parse_faq_file(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            
            if ";" in ln:
                parts = ln.split(";", 1)
                q = parts[0].strip()
                a = parts[1].strip() if len(parts) > 1 else None
                items.append((q, a))
            elif "|" in ln:
                parts = ln.split("|", 1)
                q = parts[0].strip()
                a = parts[1].strip() if len(parts) > 1 else None
                items.append((q, a))
            else:
                items.append((ln, None))
    
    return items


def build_and_save_stats_chart(save_path=None):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(1) FROM questions GROUP BY status")
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        statuses = ["pending", "answered"]
        counts = [0, 0]
    else:
        statuses = [r[0] for r in rows]
        counts = [r[1] for r in rows]
    
    plt.figure(figsize=(6, 4))
    plt.bar(statuses, counts)
    plt.title("Статус вопросов")
    plt.xlabel("Статус")
    plt.ylabel("Количество")
    plt.tight_layout()
    
    if not save_path:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        save_path = tmp.name
        tmp.close()
    
    plt.savefig(save_path)
    plt.close()
    return save_path


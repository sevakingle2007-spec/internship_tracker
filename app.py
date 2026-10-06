import os
import mysql.connector
from flask import Flask, request, redirect, render_template_string, flash, abort, url_for

app = Flask(__name__)
app.secret_key = "dev-secret"


def conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"), user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""), database="internship_db")


def run(sql, args=(), write=False):
    c = conn(); cur = c.cursor(dictionary=True)
    try:
        cur.execute(sql, args)
        if write:
            c.commit(); return cur.lastrowid
        return cur.fetchall()
    finally:
        cur.close(); c.close()


def call_proc(name, args):
    c = conn(); cur = c.cursor(dictionary=True)
    try:
        cur.callproc(name, args)
        return [r for res in cur.stored_results() for r in res.fetchall()]
    finally:
        cur.close(); c.close()


# table config: primary key, editable columns, foreign keys (col -> table, label SQL), enums
T = {
    "students": dict(pk="student_id", cols=["name", "email", "dept_id", "cgpa", "year"],
                     fk={"dept_id": ("departments", "dept_id", "dept_name")}),
    "departments": dict(pk="dept_id", cols=["dept_name"]),
    "skills": dict(pk="skill_id", cols=["skill_name", "category"]),
    "student_skills": dict(pk="student_skill_id", cols=["student_id", "skill_id", "level"],
                           fk={"student_id": ("students", "student_id", "name"),
                               "skill_id": ("skills", "skill_id", "skill_name")},
                           enums={"level": ["Beginner", "Intermediate", "Advanced"]}),
    "companies": dict(pk="company_id", cols=["company_name", "industry", "city", "contact_email"]),
    "internships": dict(pk="internship_id", cols=["title", "company_id", "stipend", "duration_months", "openings", "deadline"],
                        fk={"company_id": ("companies", "company_id", "company_name")}),
    "internship_skills": dict(pk="internship_skill_id", cols=["internship_id", "skill_id"],
                              fk={"internship_id": ("internships", "internship_id", "title"),
                                  "skill_id": ("skills", "skill_id", "skill_name")}),
    "applications": dict(pk="application_id", cols=["student_id", "internship_id", "status", "applied_on"],
                         fk={"student_id": ("students", "student_id", "name"),
                             "internship_id": ("internships", "internship_id", "title")},
                         enums={"status": ["Applied", "Shortlisted", "Interviewed", "Selected", "Rejected"]}),
    "interviews": dict(pk="interview_id", cols=["application_id", "interview_date", "mode", "result"],
                       fk={"application_id": ("applications", "application_id", "CONCAT('Application #', application_id)")},
                       enums={"mode": ["Online", "Onsite", "Phone"], "result": ["Pending", "Passed", "Failed"]}),
    "placements": dict(pk="placement_id", cols=["application_id", "offer_date", "ctc"],
                       fk={"application_id": ("applications", "application_id", "CONCAT('Application #', application_id)")}),
}
DATES = {"deadline", "applied_on", "interview_date", "offer_date"}
NUMS = {"cgpa", "year", "stipend", "duration_months", "openings", "ctc"}

BASE = """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Internship Tracker</title>
<style>
:root{--bg:#f3f6f4;--ink:#16211c;--mut:#5d6b64;--line:#d5ded9;--card:#fff;--acc:#0f6b4f;--bad:#b3261e}
@media(prefers-color-scheme:dark){:root{--bg:#101714;--ink:#e6efea;--mut:#92a39b;--line:#2a3832;--card:#17211d;--acc:#4fc79c;--bad:#ff8a80}}
*{box-sizing:border-box}body{margin:0;font:16px/1.5 Georgia,'Times New Roman',serif;background:var(--bg);color:var(--ink)}
nav{display:flex;gap:.25rem;overflow-x:auto;padding:.6rem .8rem;background:var(--acc);position:sticky;top:0}
nav a{color:#fff;text-decoration:none;padding:.3rem .7rem;border-radius:99px;white-space:nowrap;font:600 14px system-ui,sans-serif}
nav a:hover,nav a.on{background:rgba(255,255,255,.22)}
main{max-width:1000px;margin:auto;padding:1rem}
h1{font-size:1.6rem;margin:.4rem 0 1rem}h2{font-size:1.15rem;margin:1.6rem 0 .5rem}
.wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font:14px system-ui,sans-serif}
th,td{padding:.55rem .8rem;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{color:var(--mut);font-weight:600}
form.f{display:grid;gap:.8rem;max-width:480px}label{font:600 14px system-ui,sans-serif;display:grid;gap:.25rem}
input,select{font:16px system-ui,sans-serif;padding:.55rem;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
button,.btn{font:600 14px system-ui,sans-serif;background:var(--acc);color:#fff;border:0;border-radius:6px;padding:.55rem 1rem;text-decoration:none;cursor:pointer;display:inline-block}
.btn.o{background:none;color:var(--acc);border:1px solid var(--acc)}.btn.d{background:none;color:var(--bad);border:1px solid var(--bad)}
.bar{display:flex;gap:.5rem;margin-bottom:1rem;flex-wrap:wrap}.bar input{flex:1;min-width:140px}
.msg{padding:.6rem .9rem;border-radius:6px;background:var(--card);border-left:4px solid var(--bad);margin-bottom:1rem;font:14px system-ui,sans-serif}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.8rem}
.stats a{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.8rem;color:inherit;text-decoration:none}
.stats b{display:block;font-size:1.8rem}.stats span{font:14px system-ui,sans-serif;color:var(--mut)}
td form{display:inline}
</style></head><body>
<nav><a href="/" class="{{'on' if active=='home'}}">Home</a><a href="/reports" class="{{'on' if active=='reports'}}">Reports</a>
{% for t in tables %}<a href="/t/{{t}}" class="{{'on' if active==t}}">{{t.replace('_',' ').title()}}</a>{% endfor %}</nav>
<main>{% for m in get_flashed_messages() %}<div class=msg>{{m}}</div>{% endfor %}
{{ body|safe }}</main></body></html>"""


def page(body_tpl, active="", **ctx):
    body = render_template_string(body_tpl, **ctx)
    return render_template_string(BASE, body=body, active=active, tables=list(T))


TABLE_TPL = """<div class=wrap><table><tr>{% for h in heads %}<th>{{h}}</th>{% endfor %}{% if actions %}<th></th>{% endif %}</tr>
{% for r in rows %}<tr>{% for h in heads %}<td>{{r[h]}}</td>{% endfor %}
{% if actions %}<td><a class="btn o" href="/t/{{name}}/form/{{r[pk]}}">Edit</a>
<form method=post action="/t/{{name}}/delete/{{r[pk]}}" onsubmit="return confirm('Delete this row?')"><button class="d btn">Delete</button></form></td>{% endif %}</tr>
{% else %}<tr><td colspan=99>No rows found.</td></tr>{% endfor %}</table></div>"""


@app.route("/")
def home():
    counts = {t: run(f"SELECT COUNT(*) n FROM {t}")[0]["n"] for t in T}
    body = "<h1>Internship &amp; Skill Tracker</h1><div class=stats>" + "".join(
        f"<a href='/t/{t}'><b>{n}</b><span>{t.replace('_', ' ')}</span></a>" for t, n in counts.items()) + "</div>"
    return page(body, "home")


@app.route("/t/<name>")
def list_rows(name):
    if name not in T: abort(404)
    cfg, q = T[name], request.args.get("q", "").strip()
    text_cols = [c for c in cfg["cols"] if c not in NUMS | DATES and c not in cfg.get("fk", {})]
    sql = f"SELECT * FROM {name}"
    args = ()
    if q and text_cols:
        sql += " WHERE " + " OR ".join(f"{c} LIKE %s" for c in text_cols)
        args = tuple(f"%{q}%" for _ in text_cols)
    rows = run(sql + f" ORDER BY {cfg['pk']} DESC", args)
    heads = [cfg["pk"]] + cfg["cols"]
    body = f"""<h1>{name.replace('_', ' ').title()}</h1>
<form class=bar><input name=q value="{q}" placeholder="Search"><button>Search</button>
<a class=btn href="/t/{name}/form/0">Add new</a></form>""" + TABLE_TPL
    return page(body, name, rows=rows, heads=heads, name=name, pk=cfg["pk"], actions=True)


@app.route("/t/<name>/form/<int:rid>", methods=["GET", "POST"])
def form(name, rid):
    if name not in T: abort(404)
    cfg = T[name]
    if request.method == "POST":
        vals = [request.form.get(c) or None for c in cfg["cols"]]
        try:
            if rid:
                run(f"UPDATE {name} SET " + ",".join(f"{c}=%s" for c in cfg["cols"]) +
                    f" WHERE {cfg['pk']}=%s", (*vals, rid), True)
            else:
                run(f"INSERT INTO {name} ({','.join(cfg['cols'])}) VALUES ({','.join(['%s'] * len(vals))})", vals, True)
            flash("Saved.")
            return redirect(f"/t/{name}")
        except mysql.connector.Error as e:
            flash(f"Could not save: {e.msg}")
    row = (run(f"SELECT * FROM {name} WHERE {cfg['pk']}=%s", (rid,)) or [{}])[0] if rid else {}
    fields = []
    for c in cfg["cols"]:
        v = request.form.get(c, row.get(c, ""))
        v = "" if v is None else v
        if c in cfg.get("fk", {}):
            t, k, lab = cfg["fk"][c]
            opts = [(o["k"], o["l"]) for o in run(f"SELECT {k} k, {lab} l FROM {t} ORDER BY l")]
        elif c in cfg.get("enums", {}):
            opts = [(x, x) for x in cfg["enums"][c]]
        else:
            opts = None
        fields.append(dict(c=c, v=v, opts=opts,
                           type="date" if c in DATES else "number" if c in NUMS else "text"))
    body = """<h1>{{'Edit' if rid else 'Add'}} {{name.replace('_',' ')}}</h1><form class=f method=post>
{% for f in fields %}<label>{{f.c.replace('_',' ')}}
{% if f.opts %}<select name="{{f.c}}" required>{% for k,l in f.opts %}<option value="{{k}}" {{'selected' if k|string==f.v|string}}>{{l}}</option>{% endfor %}</select>
{% else %}<input name="{{f.c}}" type="{{f.type}}" value="{{f.v}}" step="any" {{'required' if f.type!='text' or f.c in ('name','email')}}>{% endif %}</label>{% endfor %}
<div class=bar><button>Save changes</button><a class="btn o" href="/t/{{name}}">Cancel</a></div></form>"""
    return page(body, name, fields=fields, rid=rid, name=name)


@app.route("/t/<name>/delete/<int:rid>", methods=["POST"])
def delete(name, rid):
    if name not in T: abort(404)
    try:
        run(f"DELETE FROM {name} WHERE {T[name]['pk']}=%s", (rid,), True)
        flash("Deleted.")
    except mysql.connector.Error as e:
        flash(f"Could not delete: {e.msg}")
    return redirect(f"/t/{name}")


@app.route("/reports")
def reports():
    iid = request.args.get("iid", type=int)
    sections = [
        ("All applications (view with 4-table join)",
         run("SELECT * FROM v_application_details ORDER BY applied_on DESC")),
        ("Students with CGPA above the average (subquery)",
         run("SELECT name, cgpa FROM students WHERE cgpa > (SELECT AVG(cgpa) FROM students) ORDER BY cgpa DESC")),
        ("Applications per company (join + group by)",
         run("""SELECT c.company_name, COUNT(a.application_id) applications
                FROM companies c LEFT JOIN internships i ON i.company_id=c.company_id
                LEFT JOIN applications a ON a.internship_id=i.internship_id
                GROUP BY c.company_id, c.company_name ORDER BY applications DESC""")),
        ("Internships with no applications yet (NOT EXISTS subquery)",
         run("""SELECT i.title, i.deadline FROM internships i
                WHERE NOT EXISTS (SELECT 1 FROM applications a WHERE a.internship_id=i.internship_id)""")),
        ("Placements (join)",
         run("""SELECT s.name student, c.company_name, p.ctc, p.offer_date FROM placements p
                JOIN applications a ON a.application_id=p.application_id
                JOIN students s ON s.student_id=a.student_id
                JOIN internships i ON i.internship_id=a.internship_id
                JOIN companies c ON c.company_id=i.company_id""")),
    ]
    internships = run("SELECT internship_id, title FROM internships")
    match = call_proc("sp_skill_match", [iid]) if iid else None
    body = """<h1>Reports</h1>
{% for title, rows in sections %}<h2>{{title}}</h2>
<div class=wrap><table>{% if rows %}<tr>{% for h in rows[0] %}<th>{{h}}</th>{% endfor %}</tr>
{% for r in rows %}<tr>{% for v in r.values() %}<td>{{v}}</td>{% endfor %}</tr>{% endfor %}
{% else %}<tr><td>No data.</td></tr>{% endif %}</table></div>{% endfor %}
<h2>Best skill matches for an internship (stored procedure)</h2>
<form class=bar><select name=iid>{% for i in internships %}<option value="{{i.internship_id}}" {{'selected' if i.internship_id==iid}}>{{i.title}}</option>{% endfor %}</select><button>Find matches</button></form>
{% if match is not none %}<div class=wrap><table><tr><th>Student</th><th>CGPA</th><th>Matched</th><th>Required</th></tr>
{% for r in match %}<tr><td>{{r.name}}</td><td>{{r.cgpa}}</td><td>{{r.matched_skills}}</td><td>{{r.required_skills}}</td></tr>
{% else %}<tr><td colspan=4>No students have the required skills.</td></tr>{% endfor %}</table></div>{% endif %}"""
    return page(body, "reports", sections=sections, internships=internships, iid=iid, match=match)


if __name__ == "__main__":
    app.run(debug=True)

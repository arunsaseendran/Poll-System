import os, io, csv, json
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, Response
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = os.environ.get("POLL_SECRET", "change-this-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "polls.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(600), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expiry = db.Column(db.DateTime, nullable=True)   # optional expiry
    active = db.Column(db.Boolean, default=True)     # admin can deactivate
    options = db.relationship("Option", backref="poll", cascade="all, delete-orphan")

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey("poll.id"), nullable=False)
    votes = db.relationship("Vote", backref="option", cascade="all, delete-orphan")

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey("poll.id"), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey("option.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'poll_id', name='uix_user_poll'),)

# ---------- Helpers ----------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or not u.is_admin:
            flash("Admin access required.", "warning")
            return redirect(url_for("index"))
        return fn(*args, **kwargs)
    return wrapper

# ---------- Auth ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        if not username or not password:
            flash("Provide username and password.", "warning")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "warning")
            return redirect(url_for("register"))
        hashed = generate_password_hash(password)
        user = User(username=username, password=hashed, is_admin=False)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["is_admin"] = user.is_admin
            flash("Logged in.", "success")
            return redirect(url_for("admin_dashboard") if user.is_admin else url_for("index"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# ---------- Index & Poll listing (users see only active polls) ----------
@app.route("/")
def index():
    now = datetime.utcnow()
    # active polls: active flag True and not expired
    polls = Poll.query.filter(Poll.active == True).order_by(Poll.created_at.desc()).all()
    # filter out expired on template side by passing now
    return render_template("index.html", polls=polls, now=now, current_user=current_user())

# ---------- Admin pages ----------
@app.route("/admin")
@admin_required
def admin_dashboard():
    polls = Poll.query.order_by(Poll.created_at.desc()).all()
    return render_template("admin.html", polls=polls)

@app.route("/admin/create", methods=["GET","POST"])
@admin_required
def create_poll():
    if request.method == "POST":
        question = request.form.get("question","").strip()
        options = request.form.getlist("options")
        options = [o.strip() for o in options if o.strip()]
        expiry_raw = request.form.get("expiry","").strip()
        active = True if request.form.get("active","on") == "on" else False
        if not question or len(options) < 2:
            flash("Provide a question and at least two options.", "warning")
            return redirect(url_for("create_poll"))
        expiry = None
        if expiry_raw:
            try:
                expiry = datetime.fromisoformat(expiry_raw)
            except Exception:
                flash("Invalid expiry format. Use the datetime picker.", "warning")
                return redirect(url_for("create_poll"))
        poll = Poll(question=question, expiry=expiry, active=active)
        db.session.add(poll)
        db.session.commit()
        for opt_text in options:
            db.session.add(Option(text=opt_text, poll_id=poll.id))
        db.session.commit()
        flash("Poll created.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("create_poll.html")

@app.route("/admin/toggle/<int:poll_id>", methods=["POST"])
@admin_required
def toggle_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    poll.active = not poll.active
    db.session.commit()
    flash("Poll status updated.", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete/<int:poll_id>", methods=["POST"])
@admin_required
def delete_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    db.session.delete(poll)
    db.session.commit()
    flash("Poll deleted.", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/results/<int:poll_id>")
@admin_required
def admin_results(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    options = poll.options
    labels = [o.text for o in options]
    votes = [Vote.query.filter_by(option_id=o.id).count() for o in options]
    total = sum(votes) or 0
    percentages = [ (v/total*100) if total>0 else 0 for v in votes ]
    payload = json.dumps({"labels": labels, "data": votes})
    return render_template("admin_results.html", poll=poll, labels=labels, data=votes, percentages=percentages, payload_json=payload)

@app.route("/admin/export/<int:poll_id>")
@admin_required
def export_poll_csv(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    options = poll.options
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["poll_id","poll_question","option_id","option_text","votes"])
    for opt in options:
        count = Vote.query.filter_by(option_id=opt.id).count()
        writer.writerow([poll.id, poll.question, opt.id, opt.text, count])
    output.seek(0)
    filename = f"poll_{poll.id}_results.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": f"attachment; filename={filename}"})

# ---------- Voting (users) ----------
@app.route("/poll/<int:poll_id>", methods=["GET","POST"])
@login_required
def poll_detail(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    now = datetime.utcnow()
    expired = poll.expiry is not None and poll.expiry < now
    if not poll.active:
        flash("This poll is currently inactive.", "warning")
    user = current_user()
    # check existing vote for this user & poll (enforce one vote per user per poll)
    existing = Vote.query.filter_by(user_id=user.id, poll_id=poll.id).first()
    if request.method == "POST":
        if expired or not poll.active:
            flash("This poll is closed; you cannot vote.", "warning")
            return redirect(url_for("index"))
        if existing:
            flash("You have already voted in this poll.", "info")
            return redirect(url_for("index"))
        option_id = request.form.get("option")
        if not option_id:
            flash("Choose an option.", "warning")
            return redirect(url_for("poll_detail", poll_id=poll.id))
        opt = Option.query.get(int(option_id))
        if not opt or opt.poll_id != poll.id:
            flash("Invalid option selected.", "danger")
            return redirect(url_for("poll_detail", poll_id=poll.id))
        vote = Vote(user_id=user.id, poll_id=poll.id, option_id=opt.id)
        try:
            db.session.add(vote)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Could not record vote. You may have already voted.", "danger")
            return redirect(url_for("index"))
        flash("Vote recorded. Thank you!", "success")
        return redirect(url_for("index"))
    return render_template("poll.html", poll=poll, expired=expired, already_voted=bool(existing))

# ---------- My Votes (user) ----------
@app.route("/my_votes")
@login_required
def my_votes():
    user = current_user()
    votes = Vote.query.filter_by(user_id=user.id).all()
    items = []
    for v in votes:
        opt = Option.query.get(v.option_id)
        poll = Poll.query.get(v.poll_id)
        items.append({
            "poll_id": poll.id,
            "poll_question": poll.question,
            "option_text": opt.text,
            "voted_at": v.created_at
        })
    return render_template("my_votes.html", votes=items)

# ---------- DB init & seed admin ----------
def seed_admin():
    if not User.query.filter_by(is_admin=True).first():
        admin_user = User(username="admin", password=generate_password_hash("admin123"), is_admin=True)
        db.session.add(admin_user)
        db.session.commit()
        print("Seeded admin -> username: admin password: admin123")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_admin()
    app.run(debug=True)

from flask import Blueprint, render_template
from dnsforever.web.tools.session import login

app = Blueprint('index', __name__)


@app.route('/')
@login(False, '/domain')
def index():
    return render_template('index.html')

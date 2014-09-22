from flask import Flask, g

from dnsforever.config import secret_key
from dnsforever.models import Session
from dnsforever.web.tools.session import get_user


blueprints = ['apis', 'index', 'account', 'domain',
              'domain_a', 'domain_aaaa', 'domain_cname', 'domain_mx',
              'domain_txt']


def create_app():
    app = Flask(__name__)
    app.secret_key = secret_key

    for name in blueprints:
        app.register_blueprint(load_blueprint(name))

    @app.before_request
    def define_session():
        g.service_name = 'DNS Forever (alpha)'
        g.session = Session()

        g.user = get_user()
        if g.user:
            g.domain_list = [ownership.domain.name
                             for ownership in g.user.ownership]
        else:
            g.domain_list = []

        g.debug = app.debug

    return app


def load_blueprint(name):
    module = __import__('dnsforever.web.' + name, None, None, ['app'])
    blueprint = getattr(module, 'app')
    return blueprint

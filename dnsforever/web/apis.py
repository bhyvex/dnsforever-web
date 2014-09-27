import string
import re
from datetime import datetime, tzinfo, timedelta

from flask import Blueprint, g, request
from flask.ext import restful
from flask.ext.restful import reqparse

from dnsforever.models import Domain, Record, RecordDDNS_A, NameServer

app = Blueprint('apis', __name__, url_prefix='/apis')
api = restful.Api(app)


class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)


def totimestamp(dt, epoch=datetime(1970, 1, 1)):
    td = dt - epoch
    return int(td.total_seconds())


def todatetime(ts, epoch=datetime(1970, 1, 1)):
    return datetime.fromtimestamp(ts, UTC())


class ServerUpdate(restful.Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('last_update', type=int, default=None)
        args = parser.parse_args()

        ns = g.session.query(NameServer)\
                      .filter(NameServer.ip == request.remote_addr).first()

        if not ns and not g.debug:
            return 'ERROR', 403

        update_query = g.session.query(Domain)
        if args.last_update:
            last_update = todatetime(args.last_update)
            update_query = update_query.filter(Domain.updated_at > last_update)
        domains = update_query.all()

        result = {}
        for domain in domains:
            records = g.session.query(Record)\
                               .filter(Record.domain == domain)\
                               .all()

            records = [string.join([record.name or '@',
                                    record.type, record.rdata], ' ')
                       for record in records]

            soa_record = '@ SOA ns1.dnsforever.kr. root.%s. '\
                         '%d 3600 600 86400 3600' %\
                         (domain.name, domain.update_serial)
            records.insert(0, soa_record)

            domain_info = {'records': records,
                           'last_update': totimestamp(domain.updated_at)}

            result[domain.name] = domain_info

        return result

api.add_resource(ServerUpdate, '/server/update')


class DdnsUpdate(restful.Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('key', type=str, required=True)
        parser.add_argument('host', type=str, required=True)
        parser.add_argument('ip', type=str)
        args = parser.parse_args()

        record = g.session.query(RecordDDNS_A)\
                          .filter(RecordDDNS_A.ddns_key == args['key'])\
                          .first()

        if not record:
            return 'ERROR', 404

        if record.name:
            host = '%s.%s' % (record.name, record.domain.name)
        else:
            host = record.domain.name

        if host != args['host']:
            return 'ERROR', 404

        if 'ip' in args and args['ip']:
            record.ip = args['ip']
        else:
            record.ip = request.remote_addr

        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', record.ip):
            return 'ERROR', 404

        with g.session.begin():
            record.update()
            g.session.add(record)

        return 'OK'

api.add_resource(DdnsUpdate, '/ddns')

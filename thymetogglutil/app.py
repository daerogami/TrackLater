from flask import Flask, request, render_template
from thymetogglutil.main import Parser
from thymetogglutil import settings
from datetime import datetime, timedelta
import json
import pytz

from thymetogglutil.timemodules.interfaces import Entry, AddEntryMixin, UpdateEntryMixin

app = Flask(__name__)

parser = None

logger = app.logger


@app.route("/")
def hello():
    return render_template(
        'index.html'
    )


@app.route('/listmodules', methods=['GET'])
def listmodules():
    if request.method == 'GET':
        data = settings.ENABLED_MODULES
        return json.dumps(data, default=str)


@app.route('/fetchdata', methods=['GET'])
def fetchdata():
    if request.method == 'GET':
        keys = request.values.get('keys[]', 'all')
        now = datetime.now()
        if 'from' in request.values:
            from_date = parseTimestamp(request.values['from'])
        else:
            from_date = now - timedelta(days=14)

        if 'to' in request.values:
            to_date = parseTimestamp(request.values['to'])
        else:
            to_date = now

        parser = Parser(from_date, to_date)
        parser.parse()
        data = {}
        for key in settings.ENABLED_MODULES:
            if keys == "all" or key in keys:
                data[key] = {}
                data[key]['entries'] = [entry.to_dict()
                                        for entry in parser.modules[key].entries]
                data[key]['projects'] = [project.to_dict()
                                         for project in parser.modules[key].projects]
                data[key]['issues'] = [issue.to_dict()
                                       for issue in parser.modules[key].issues]
        return json.dumps(data, default=str)


def parseTimestamp(stamp):
    if not stamp:
        return None
    tz = pytz.timezone('Europe/Helsinki')
    date = datetime.fromtimestamp(int(stamp) / 1e3, tz)
    return date


@app.route('/updateentry', methods=['POST'])
def updateentry():
    if request.method == 'POST':
        module = request.values.get('module')
        entry_id = request.values.get('entry_id', None)
        new_entry = Entry(
            start_time=parseTimestamp(request.values['start_time']),
            end_time=parseTimestamp(request.values.get('end_time', None)),
            id=entry_id,
            issue=request.values.get('issue_id', None),
            project=request.values['project_id'],
            title=request.values.get('title', ''),
            text=request.values.get('text', []),
            extra_data=request.values.get('extra_data', {})
        )
        issue = None
        if new_entry.issue:
            for module in settings.ENABLED_MODULES:
                _tmp = parser.modules[module].find_issue(new_entry.issue)
                if _tmp:
                    issue = _tmp
                    break

        if not entry_id:
            # Check that create is allowed
            assert isinstance(parser.modules[module], AddEntryMixin)
            parser.modules[module].create_entry(
                new_entry=new_entry,
                issue=issue
            )
        else:
            # Check that update is allowed
            assert isinstance(parser.modules[module], UpdateEntryMixin)
            parser.modules[module].update_entry(
                entry_id=new_entry.id,
                new_entry=new_entry,
                issue=issue
            )

        data = {}
        data[module]['entries'] = [entry.to_dict() for entry in parser.modules[module].entries]
        return json.dumps(data, default=str)


@app.route('/deleteentry', methods=['POST'])
def deleteentry():
    if request.method == 'POST':
        ret = parser.delete_time_entry(request.form.get('id'))
        module = request.values.get('module')
        entry_id = request.values.get('entry_id', None)

        # Check that delete is allowed
        assert isinstance(parser.modules[module], AddEntryMixin)
        parser.modules[module].delete_entry(
            entry_id=entry_id
        )

        data = {}
        data[module]['entries'] = [entry.to_dict() for entry in parser.modules[module].entries]
        return json.dumps(data, default=str)

        return json.dumps(ret, default=str)

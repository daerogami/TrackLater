#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
from datetime import date, datetime, timedelta, tzinfo
from dateutil import parser as dateparser
from colorama import Fore, Style
import requests
import json
import settings
import time
import git

parser = ArgumentParser()
parser.add_argument("-f", "--file", dest="filename",
                    help="json file to parse", metavar="FILE")
parser.add_argument("-d", "--date", dest="date",
                    help="date")
parser.add_argument("-y", "--yesterday", dest="yesterday",
                    help="yesterday")
parser.add_argument("-n", "--consecutive", dest="consecutive",
                    help="consecutive", type=int)
parser.add_argument("-c", "--cutoff", dest="cutoff",
                    help="cutoff", default=900, type=int)
parser.add_argument("-a", "--api_key", dest="api_key",
                    help="api_key")

def main():
    filename = args.filename
    if not filename:
        if args.date:
            _date = datetime.strptime(args.date, '%Y-%m-%d')
        else:
            _date = date.today() - timedelta(days=int(args.yesterday or 0))
        filename = '../thyme/{}.json'.format(_date.strftime('%Y-%m-%d'))

    toggl.start_date = datetime.combine(_date - timedelta(days=1), datetime.min.time(), )

    filenames = [filename]
    if args.consecutive:
        for i in range(args.consecutive):
            _date = _date + timedelta(days=1)
            filenames.append('../thyme/{}.json'.format(_date.strftime('%Y-%m-%d')))

    toggl.end_date = datetime.combine(_date + timedelta(days=1), datetime.min.time())

    toggl.time_entries = toggl.get_time_entries()

    sessions = SessionGenerator()

    for filename in filenames:
        print("opening file {}".format(filename))
        with open(filename) as f:
            data = json.load(f)
            snapshots = data.get('Snapshots')
            sessions.add(snapshots)
    
    sessions.generate()
    
    while True:
        print_sessions(sessions)
        uinput = raw_input("select command (w, p, q): ")
        if uinput not in ['w', 'p', 'q']:
            continue
        command = uinput
        if command == 'q':
            break
        uinput = raw_input("Select session (1-{}): ".format(len(sessions.sessions)))
        try:
            selection = parse_selection(uinput)
            if command == 'w':
                for i in selection:
                    sessions.sessions[i].print_windows()
            elif command == 'p':
                name = raw_input("Name: ")
                if uinput == 'q':
                    continue
                for i in selection:
                    toggl.push_session(sessions.sessions[i], name)
            time.sleep(2)
        except Exception as e:
            raise

def parse_selection(uinput):
    if '-' in uinput:
        vals = [int(i)-1 for i in uinput.split('-')]
        return range(vals[0], vals[1]+1)
    return [int(uinput)-1]

def print_sessions(sessions):
    count = 1
    for session in sessions.sessions:
        entry_id = toggl.check_session_exists(session)
        category = session.guess_category()
        if category == 'work':
            color = Fore.RED
            if entry_id:
                color = Fore.GREEN
                if not toggl.get_entry(entry_id).get('description', None):
                    color = Fore.MAGENTA
        else:
            color = Fore.GREEN
            if entry_id:
                color = Fore.RED
        print u"{}{}. {} {} - {}{}".format(color,
            count, session.print_out(out=False),
            u'exported: {}'.format(toggl.get_entry(entry_id).get('description', '')) if entry_id else '',
            category,
            Style.RESET_ALL
        )
        print ""
        for window in session.sorted_windows()[-3:]:
            print u"    {}s - {}".format(
                session.windows[window], window
            )
        print ""
        for commit in gitparser.get_commits(session.start_time, session.end_time):
            print u"    {}".format(
                commit['message']
            )
        print ""
        count += 1

class Toggl():
    def __init__(self, api_key):
        self.api_key = api_key
        response = requests.get('https://www.toggl.com/api/v8/me', auth=(self.api_key, 'api_token'))
        data = response.json()['data']
        self.email = data['email']
        self.default_wid = data['default_wid']
        self.id = data['id']
        self.start_date = None
        self.end_date = None
        self.time_entries = self.get_time_entries()
        self.check_overlap()

    def push_session(self, session, name):
        if session.guess_category() == 'leisure':
            print "skipping - leisure"
            return
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            'time_entry': {
                "description": name,
                "start": session.start_time.isoformat(),
                "duration":(session.end_time - session.start_time).seconds,
                "created_with":"thyme-toggl-cli"
            }
        }
        entry_id = self.check_session_exists(session)
        if entry_id:
            del data['time_entry']['start']
            del data['time_entry']['duration']
            self.update_time_entry(entry_id, data)
            return
        response = requests.post(
            'https://www.toggl.com/api/v8/time_entries',
            data=json.dumps(data), headers=headers, auth=(self.api_key, 'api_token'))
        print(u'Pushed session to toggl: {}'.format(response.text))
        self.time_entries = self.get_time_entries()
        pass

    def update_time_entry(self, entry_id, data):
        response = requests.put('https://www.toggl.com/api/v8/time_entries/{}'.format(entry_id), data=json.dumps(data), auth=(self.api_key, 'api_token'))
        print(u'Updated session to toggl: {}'.format(response.text))
        self.time_entries = self.get_time_entries()
        return response.json()

    def get_time_entries(self):
        if self.start_date:
            params = {'start_date': self.start_date.isoformat() + "+03:00", 'end_date': self.end_date.isoformat() + "+03:00"}
        else:
            params = {}
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.get('https://www.toggl.com/api/v8/time_entries', headers=headers, params=params, auth=(self.api_key, 'api_token'))
        return json.loads(response.text)
    
    def check_overlap(self):
        for entry1 in self.time_entries:
            for entry2 in self.time_entries:
                if entry1 == entry2:
                    continue
                start1 = parse_time(entry1['start'])
                stop1 = parse_time(entry1['stop'])
                start2 = parse_time(entry2['start'])
                stop2 = parse_time(entry2['stop'])
                if start1 <= start2 <= stop1:
                    print "OVERLAP IN ENTRY {}".format(start1)
                elif start1 <= stop2 <= stop1:
                    print "OVERLAP IN ENTRY {}".format(start1)
                elif start1 <= start2 and stop2 <= stop1:
                    print "OVERLAP IN ENTRY {}".format(start1)

        return None
    
    def get_entry(self, entry_id):
        for entry in self.time_entries:
            if entry['id'] == entry_id:
                return entry
    
    def check_session_exists(self, session):
        for entry in self.time_entries:
            start = parse_time(entry['start'])
            stop = parse_time(entry['stop'])
            if start <= session.start_time <= stop:
                return entry['id']
            if start <= session.end_time <= stop:
                return entry['id']
            if session.start_time <= start and stop <= session.end_time:
                return entry['id']
            if start <= session.start_time and session.end_time <= stop:
                return entry['id']
        return None

def parse_time(timestr):
    return dateparser.parse(timestr)

def get_window_name(snapshot):
    if snapshot is None:
        return None
    for window in snapshot['Windows']:
        if window['ID'] == snapshot['Active']:
            return window['Name']


class Session():
    def print_out(self, out=True):
        duration = (self.end_time - self.start_time)
        print_str = u"{}, time: {}".format(
            self.start_time.strftime('%a %d.%m %H:%M'),
            str(duration)[:-10]
        )
        if out:
            print print_str
        return print_str

    def sorted_windows(self):
        return sorted(self.windows, key=lambda x: self.windows[x])

    def print_windows(self):
        for window in self.sorted_windows():
            print u"{}s - {}".format(self.windows[window], window)

    def guess_category(self):
        top_windows = self.sorted_windows()[-3:]
        medium_windows = self.sorted_windows()[-6:-3]
        score = dict(settings.SCORE)
        for window in top_windows:
            for l in settings.LEISURE:
                if l in window:
                    score['leisure'] += 2
                    break
            for l in settings.WORK:
                if l in window:
                    score['work'] += 2
                    break
        for window in medium_windows:
            for l in settings.LEISURE:
                if l in window:
                    score['leisure'] += 1
                    break
            for l in settings.WORK:
                if l in window:
                    score['work'] += 1
                    break
        return max(score.iterkeys(), key=(lambda key: score[key]))

    def __init__(self, time):
        self.start_time = time
        self.end_time = None
        self.windows = {}
        self.running = True

    def end(self, time):
        if self.end_time:
            return
        self.end_time = time
        self.running = False
    
    def add_window(self, diff, window_name):
        if 'eero@eero-ThinkPad-L470' in window_name:
            return
        if window_name not in self.windows:
            self.windows[window_name] = 0
        self.windows[window_name] += diff.seconds


class SessionGenerator():
    def __init__(self):
        self.sessions = []
        self.snapshots = []

    def add(self, snapshots):
        self.snapshots += snapshots
    
    def print_sessions(self):
        for session in self.sessions:
            session.print_out()

    def start_or_continue_session(self, time, diff=None, window=None):
        if len(self.sessions) > 0 and self.sessions[-1].running:
            if window:
                self.sessions[-1].add_window(diff, window)
            return

        self.sessions.append(Session(time))

    def end_session(self, time):
        self.sessions[-1].end(time)
    
    def generate(self):
        new_time = None
        prev_snapshot = None
        last_active = 0
        for snapshot in self.snapshots:
            if snapshot['Active'] == last_active:
                continue
            prev_time = new_time
            new_time = parse_time(snapshot['Time'])
            if not prev_time:  # first loop
                continue
            diff = new_time - prev_time
            if diff.seconds < args.cutoff:
                self.start_or_continue_session(prev_time, diff=diff, window=get_window_name(prev_snapshot))
            else:
                self.end_session(prev_time)
            prev_snapshot = snapshot
            last_active = snapshot['Active']
        self.end_session(new_time)

class GitParser():
    def __init__(self, repos):
        self.repos = repos
        self.log = []  # List of git.refs.log.RefLogEntry objects
    
    def parse(self):
        for repo_path in self.repos:
            repo = git.Repo(repo_path)
            for branch in repo.branches:
                for log_entry in branch.log():
                    if log_entry.actor.email not in settings.GIT_EMAILS:
                        continue
                    if not log_entry.message.startswith('commit'):
                        continue
                    message = ''.join(log_entry.message.split(':')[1:])
                    self.log.append({
                        'repo': repo_path.split('/')[-1],
                        'message': message,
                        'time': datetime.fromtimestamp(
                            log_entry.time[0], tz=FixedOffset(log_entry.time[1], 'Helsinki')
                        ),
                    })
    
    def get_commits(self, start_time, end_time):
        ret = []
        for log in self.log:
            if start_time <= log['time'] <= end_time:
                ret.append(log)
        return ret

    def print_commits(self, out=True, sort='time'):
        print_str = (
            "\n".join(['{} - {} - {}'.format(
                log['time'], log['repo'], log['message']
            ) for log in sorted(self.log, key=lambda x: x[sort])])
        )
        if out:
            print(print_str)
        return print_str

class FixedOffset(tzinfo):
    """Fixed offset in minutes west from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(seconds = -offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return timedelta(0)

if __name__ == '__main__':
    args = parser.parse_args()
    toggl = Toggl(args.api_key or settings.API_KEY)
    gitparser = GitParser(settings.GIT_REPOS)
    gitparser.parse()
    main()
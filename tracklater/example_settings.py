
# Rename to `user_settings.py` and edit to your liking.

ENABLED_MODULES = [
    'thyme',
    'gitmodule',
    'toggl',
    'taiga',
    'jira',
    'slack'
]

UI_SETTINGS = {
    'toggl': {
        'global': '#E01A22'
    },
    'thyme': {
        'global': '#1aef65'
    },
    'gitmodule': {
        'global': '#F44D27'
    },
    'slack': {
        'global': '#4A154B'
    }
}

# Toggl module supports a single login using an api key.

TOGGL = {
    'global': {
        'API_KEY': 'your-api-key'
    },
    'group1': {
        # NAME Must match the client name on toggl
        'NAME': 'First Group',
        'PROJECTS': {
            # PROJECTS Keys must match the project name on toggl.
            # Values contain a project type, currently unused.
            'Development': 'default',
            'Bug fixing': 'bug',
        }
    },
    'group2': {
        'NAME': 'Second Group',
        'PROJECTS': {
            'Development': 'default',
            'Bug fixing': 'default',
        }
    }
}

GIT = {
    'global': {
        # Only commits made by users with EMAILS will be shown
        'EMAILS': ['firstname.lastname@email.com'],
    },
    'group1': {
        # Full path to the git repo
        'REPOS': ['/full/path/to/group1/repo']
    },
    'group2': {
        'REPOS': ['/full/path/to/group2/repo']
    },
}

JIRA = {
    'group1': {
        # Each group must have these settings
        'CREDENTIALS': ('username', 'password'),
        'URL': 'https://group1.atlassian.net',
        'PROJECT_KEY': 'DEV',
    }
}

TAIGA = {
    'global': {
        'CREDENTIALS': ['username', 'password']
    },
    'group2': {
        # project_slug can be found in the URL
        'project_slug': 'username-group2'
    }
}

THYME = {
    'global': {
        # Directory containing the json files generated by thyme
        'DIR': '/full/path/to/thyme/dir',
    }
}

SLACK = {
    # Each group should contain a workspace to match all messager to a group
    'global': {
        # Global catch-all workspace for all groups
        'API_KEY': 'legacy-slack-api-key-global',
        'USER_ID': 'your-user-id',
    },
    'group2': {
        # Messages in this workspace will be matched to group2
        'API_KEY': 'legacy-slack-api-key-group2',
        'USER_ID': 'your-user-id',
    }
}
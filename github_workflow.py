import argparse
import os
import subprocess
from datetime import datetime
from pydantic import BaseModel

class CommitDetail(BaseModel):
    message: str
    author: str
    email: str
    date: datetime

class VersionDetails(BaseModel):
    current_version: str
    next_version: str
    bump_type: str
    commit_messages: list[CommitDetail]
    tags: list[str]
    pr_labels: list[str]

class GithubWorkflow:
    def __init__(self):
        self.minor_count = 0
        self.patch_count = 0
        self.breaking_count = 0

    def set_git_config(self, email='user@example.com', name='GitHub User'):
        subprocess.check_call(['git', 'config', '--global', 'user.email', email])
        subprocess.check_call(['git', 'config', '--global', 'user.name', name])
        return "Git configuration set successfully."

    def process_arguments(self):
        parser = argparse.ArgumentParser(description="Manage GitHub workflow tasks.")
        parser.add_argument('--config-git', action='store_true', help='Configure Git with default user details.')
        parser.add_argument('--branch-name', type=str, help='The branch name for file paths, required for versioning tasks.')
        parser.add_argument('--pr-labels', type=str, default='', help='Comma-separated PR labels, optional.')

        args = parser.parse_args()

        if args.config_git:
            print(self.set_git_config())
        elif args.branch_name:
            # Ensuring branch-name argument is provided for versioning tasks
            print(self.write_version_details_to_file(args.branch_name, args.pr_labels))
        else:
            # This error will only be raised if neither config-git is used nor branch-name is provided for other tasks
            parser.error("Branch name is required for versioning tasks unless configuring git.")

    def write_version_details_to_file(self, branch_name, pr_labels):
        current_version = self.get_current_version()
        commit_messages = self.fetch_commit_messages(current_version)
        next_version = self.determine_next_version(current_version)
        version_details = VersionDetails(
            current_version=current_version,
            next_version=next_version,
            bump_type=self.determine_version_bump(),
            commit_messages=commit_messages,
            tags=self.fetch_tags(),
            pr_labels=pr_labels.split(',')
        )
        directory = f".artifacts/{branch_name}"
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, "version_details.json")
        with open(file_path, 'w') as file:
            file.write(version_details.json(indent=4))
        return f"Version details written to {file_path}"

    def get_current_version(self):
        tags = self.fetch_tags()
        if tags:
            sorted_tags = sorted(tags, key=lambda x: tuple(map(int, x.strip('v').split('.'))))
            return sorted_tags[-1]
        return 'v0.0.0'

    def fetch_tags(self):
        try:
            return subprocess.check_output(['git', 'tag'], text=True).strip().split()
        except subprocess.CalledProcessError:
            return []

    def fetch_commit_messages(self, current_version):
        commands = ['git', 'log', f'{current_version}..HEAD', '--pretty=format:%H|%an|%ae|%ad|%s']
        raw_commits = subprocess.check_output(commands, text=True)
        return [
            CommitDetail(
                message=line.split('|')[4],
                author=line.split('|')[1],
                email=line.split('|')[2],
                date=datetime.strptime(line.split('|')[3], '%a %b %d %H:%M:%S %Y %z')
            ) for line in raw_commits.strip().split('\n') if line
        ]

    def determine_next_version(self, current_version):
        parts = list(map(int, current_version.strip('v').split('.')))
        if self.breaking_count > 0:
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif self.minor_count > 0:
            parts[1] += 1
            parts[2] = 0
        elif self.patch_count > 0:
            parts[2] += 1
        return 'v' + '.'.join(map(str, parts))

    def determine_version_bump(self):
        if self.breaking_count > 0:
            return "Major"
        elif self.minor_count > 0:
            return "Minor"
        elif self.patch_count > 0:
            return "Patch"
        return "None"

if __name__ == "__main__":
    workflow = GithubWorkflow()
    workflow.process_arguments()

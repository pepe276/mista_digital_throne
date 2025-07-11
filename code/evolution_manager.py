
import os
from github import Github, Auth

class EvolutionManager:
    def __init__(self):
        self.app_id = os.environ.get("GITHUB_APP_ID")
        self.private_key = os.environ.get("GITHUB_PRIVATE_KEY")
        self.installation_id = os.environ.get("GITHUB_INSTALLATION_ID")
        self.repo_name = os.environ.get("GITHUB_REPO_NAME") # e.g., 'pepe276/mista-next-app'

        if not all([self.app_id, self.private_key, self.installation_id, self.repo_name]):
            raise ValueError("Missing one or more GitHub environment variables.")

        self.auth = Auth.AppAuth(self.app_id, self.private_key)
        self.gi = self.auth.get_installation_auth(self.installation_id)
        self.g = Github(auth=self.gi)
        self.repo = self.g.get_repo(self.repo_name)

    def get_file_content(self, file_path):
        contents = self.repo.get_contents(file_path)
        return contents.decoded_content.decode()

    def update_file(self, file_path, new_content, commit_message):
        contents = self.repo.get_contents(file_path)
        self.repo.update_file(contents.path, commit_message, new_content, contents.sha)

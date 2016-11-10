#! /usr/local/bin/python

import argparse
import os
import shutil
import sys
import tempfile

import git

#IGNORE_PATTERNS = ('.git', ".DS_Store")
SAFE_CHARS = ["-", "_", "."]
MAX_LENGTH = 100

#STUDENT = "student"
DEVELOP_PATTERN = "develop-"
#DEVELOP_DEFAULT = "all develop branches"

DIFF_FORMAT = """

You can download a zip of this exercise [here](https://github.com/udacity/ud843-QuakeReport/archive/{number}-Exercise-{name}.zip), \
and a zip of the solution [here](https://github.com/udacity/ud843-QuakeReport/archive/{number}-Solution-{name}.zip). \
Also, you can find a visual summary of the solution [here](https://github.com/udacity/ud843-QuakeReport/compare/\
{number}-Exercise-{name}...{number}-Solution-{name}).

"""


def flatten(repo_dir, target_dir, student, develop_branches, remove_branches, links):
    repo = git.Repo(repo_dir)

    if develop_branches == DEVELOP_DEFAULT:
        develop_branches = [
            branch for branch in repo.branches if DEVELOP in branch.name]

    if remove_branches:
        remove_local_branches(repo, student, develop_branches)

    flat = len(develop_branches) == 1

    # print develop_branches

    try:
        temp_dir = tempfile.mkdtemp()
        try:
            current_branch = repo.active_branch
            print "Stashing"
            repo.git.stash()

            for develop in develop_branches:
                to_temp_dir(repo, repo_dir, develop, temp_dir, flat, links)
            if links:
                insert_diff_links(temp_dir)

            copy_snapshots(repo, student, temp_dir, target_dir)
        finally:
            if current_branch:
                repo.git.checkout(current_branch)
            print "Popping"
            if repo.git.stash("list"):
                repo.git.stash("pop")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    print "Done! Review and commit the", student, "branch at your leisure."
    print "Then run $ git push --all --prune"


def remove_local_branches(repo, student, develop_branches):
    for branch in repo.branches:
        if branch.name != student and branch not in develop_branches:
            print "Removing local branch:", branch.name
            repo.git.branch(branch.name, "-D")


def to_temp_dir(repo, repo_dir, develop, temp_dir, flat, links):
    for rev in repo.git.rev_list(develop).split("\n"):
        commit = repo.commit(rev)
        branch_name = cleanCommitMessage(commit.message)
        if "Exercise" in branch_name or "Solution" in branch_name:
            if branch_name in repo.branches:
                repo.git.branch(branch_name, "-D")
            new_branch = repo.create_head(branch_name)
            new_branch.set_commit(rev)

            repo.git.checkout(commit)
            print "Saving snapshot of:", branch_name
            repo.git.clean("-fdx")
            if flat:
                target_dir = os.path.join(temp_dir, branch_name)
            else:
                folder_name = develop.name.split("-", 1)[1]
                target_dir = os.path.join(temp_dir, folder_name, branch_name)

            shutil.copytree(repo_dir, target_dir,
                            ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))

            if links:
                with open(os.path.join(target_dir, "README.md"), "a") as readme:
                    print branch_name
                    number, _, name = branch_name.split("-")
                    readme.write(DIFF_FORMAT.format(number=number, name=name))


def cleanCommitMessage(message):
    first_line = message.split("\n")[0]
    safe_message = "".join(
        c for c in first_line if c.isalnum() or c in SAFE_CHARS).strip()
    return safe_message[:MAX_LENGTH] if len(safe_message) > MAX_LENGTH else safe_message


def insert_diff_links(temp_dir):
    for item in os.listdir(temp_dir):
        number, _, name = item.split("-")
        with open(os.path.join(temp_dir, item, "README.md"), "a") as readme:
            readme.write(DIFF_FORMAT.format(number=number, name=name))


def copy_snapshots(repo, student, temp_dir, target_dir):
    if target_dir == os.getcwd():
        repo.git.checkout(student)
    for item in os.listdir(temp_dir):
        source_dir = os.path.join(temp_dir, item)
        dest_dir = os.path.join(target_dir, item)

        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        print "Copying: ", item
        shutil.copytree(source_dir, dest_dir)


GITHUB_FOLDER_BASE_URL = "https://github.com/udacity/ud851-Exercises/tree/student/"
GITHUB_DIFF_URL = "https://github.com/udacity/ud851-Exercises/compare/{before}...{after}"
DOWNLOAD_FILENAME = "{folderName}-DOWNLOAD.md"
MARKDOWN_DOWNLOAD_FORMAT = """
# {appName} Code
The code for this app can be found in the [{folderName}]({folderLink}) folder of the [Toy App Repository](https://github.com/udacity/ud851-Exercises).

If you need to a refresher on how the code is organized, please refer the [concept where we introduced the code flow](https://classroom.udacity.com/courses/ud851/lessons/93affc67-3f0b-4f9b-b3a4-a7a26f241a86/concepts/115d08bb-f114-46fa-b693-5c6ce1445c07).

## Explanation of {appName}
TODO INSERT ANY EXPLANATION OF THE APP NEEDED
 """

EXERCISE_SOLUTION_FILENAME = "{folderName}-EXERCISES-SOLUTIONS.md"
MARKDOWN_EXERCISE = """
### Exercise Code
**Exercise:** [{exerciseName}]({exerciseFolder})
"""

MARKDOWN_TOY_SOLUTION = """
**Solution:** [[{folderName}]({folderLink})][[Diff]({diffLink})]
"""

MARKDOWN_SUNSHINE_SOLUTION = """
# <Name of Node> Solution

<Description of the solution state, what the app can now do, etc>

## Notes on Solution Code

<Description of any interesting things you want to point out, gotchas, etc>

### Solution Code
**Solution:** [[{folderName}]({folderLink})][[Diff]({diffLink})]
"""


class BranchText:

    def __init__(self, branch, outputDir):
        branchName = branch.name
        self.branch = branch
        self.branchName = branchName
        self.folderName = branchName.replace(DEVELOP_PATTERN, "")
        self.folderLink = GITHUB_FOLDER_BASE_URL + self.folderName
        self.appName = " ".join(self.folderName.split("-")[1:])
        self.directory = os.path.join(outputDir, self.folderName)

    def __repr__(self):
        return "Branch %s : %s \n %s \n %s \n" % (self.branchName, self.folderName, self.folderLink, self.directory)

    def makeBranchFolderWithDownloadText(self):
        # Make a directory if non exists
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        # Make the download text
        filename = DOWNLOAD_FILENAME.format(folderName=self.folderName)
        print filename
        with open(os.path.join(self.directory, filename), "w") as downloadText:
            downloadText.write(
                MARKDOWN_DOWNLOAD_FORMAT.format(appName=self.appName,
                 folderName=self.folderName,
                 folderLink=self.folderLink))

    def makeExerciseSolutionFile(self, repo, sunshineStyle):
        stringToWrite = ""
        for rev in repo.git.rev_list(self.branchName,reverse=True).split("\n"):
            commit = repo.commit(rev)
            curStepBranchName = cleanCommitMessage(commit.message)
            print curStepBranchName
            if "Exercise" in curStepBranchName:
                # Generate exercise text
                curExerciseName = curStepBranchName
                curExerciseFolder = self.folderLink + "/" + curStepBranchName
                curExerciseString = MARKDOWN_EXERCISE.format(
                    exerciseName=curExerciseName,
                    exerciseFolder=curExerciseFolder)
                stringToWrite = stringToWrite + "\n\n" + curExerciseString

                # Generate solution text
                curSolutionName = curExerciseName.replace("Exercise","Solution")
                curDiffLink = GITHUB_DIFF_URL.format(
                    before=curExerciseName,
                    after=curSolutionName)
                curSolutionString = ""
                if sunshineStyle:
                    curSolutionString = MARKDOWN_SUNSHINE_SOLUTION.format(
                        folderName=self.folderName,
                        folderLink=self.folderLink,
                        diffLink=curDiffLink)
                else:
                    curSolutionString = MARKDOWN_TOY_SOLUTION.format(
                        folderName=self.folderName,
                        folderLink=self.folderLink,
                        diffLink=curDiffLink)

                stringToWrite = stringToWrite + "\n\n" + curSolutionString



        filename = EXERCISE_SOLUTION_FILENAME.format(
                folderName=self.folderName)
        with open(os.path.join(self.directory, filename), "w") as exerciseSolutionText:
            exerciseSolutionText.write(stringToWrite)

def makeTextAtoms(repoDir, targetDir, sunshineStyle):
    print "Sunshine style is " + str(sunshineStyle)
    repoDir = repoDir.strip()
    targetDir = targetDir.strip()
    print repoDir
    print targetDir
    # get the develop branches
    repo = git.Repo(repoDir)
    startingBranch = repo.active_branch
    print "Stashing"
    repo.git.stash()

    branchTexts = []
    for branch in repo.branches:
        if DEVELOP_PATTERN in branch.name:
            curBranchText = BranchText(branch, targetDir)
            branchTexts.append(curBranchText)
            curBranchText.makeBranchFolderWithDownloadText()
            curBranchText.makeExerciseSolutionFile(repo, sunshineStyle)

    print branchTexts
    #popping
    if startingBranch:
        repo.git.checkout(startingBranch)
    print "Popping"
    if repo.git.stash("list"):
        repo.git.stash("pop")


    #branchDir = makeDirectory(targetDir)
    # makeDownloadFile(branchDir)

    # in the output directory, make a folder for each of the develop branches
    # go through all the commits of that develop, for every one that has the
    # word exercise, generate

DESCRIPTION = "A script that makes markdown exercise and solution text for a very specifically formatted github repo "


def main():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-r', '--repo',
                        default=os.getcwd(),
                        help="the directory of the source repository")

    parser.add_argument('-o', '--output',
                        default=os.path.abspath('output'),
                        help="output directory")

    parser.add_argument('-s', '--sunshinestyle',
                    action='store_true',
                    help="whether text should be sunshine style solution markdown")

    parsed = parser.parse_args()

    makeTextAtoms(
        parsed.repo,
        parsed.output,
        parsed.sunshinestyle,
    )


if __name__ == "__main__":
    sys.exit(main())

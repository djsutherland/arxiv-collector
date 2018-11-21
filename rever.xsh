$PROJECT = $GITHUB_REPO = 'arxiv-collector'
$GITHUB_ORG = 'dougalsutherland'

$ACTIVITIES = [
    'version_bump',
    'changelog',
    'tag',
    'push_tag',
    'pypi',
    'ghrelease',
    # 'conda_forge',
]
$VERSION_BUMP_PATTERNS = [  # These note where/how to find the version numbers
    ('arxiv_collector.py', '__version__\s*=.*', "__version__ = '$VERSION'"),
    ('setup.py', 'version\s*=.*,', "version='$VERSION',")
]

$CHANGELOG_FILENAME = 'CHANGELOG.rst'
$CHANGELOG_TEMPLATE = 'TEMPLATE.rst'

$PROJECT = $GITHUB_REPO = 'arxiv-collector'
$GITHUB_ORG = 'djsutherland'

$ACTIVITIES = [
    'version_bump',
    'changelog',
    'tag',
    'push_tag',
    'pypi',
    'ghrelease',
    'conda_forge',
]
$VERSION_BUMP_PATTERNS = [  # These note where/how to find the version numbers
    ('arxiv_collector.py', r'__version__\s*=.*', '__version__ = "$VERSION"'),
    ('setup.py', r'version\s*=.*,', 'version="$VERSION",')
]

$CHANGELOG_FILENAME = 'CHANGELOG.rst'
$CHANGELOG_TEMPLATE = 'TEMPLATE.rst'
$CONDA_FORGE_SOURCE_URL = 'https://pypi.io/packages/source/a/arxiv-collector/arxiv-collector-$VERSION.tar.gz'

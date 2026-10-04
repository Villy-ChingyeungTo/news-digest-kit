"""Build a source-only ZIP. Runtime configuration is never eligible."""
from pathlib import Path
import argparse
import zipfile

FILES = [
    'digest.py','ui.py','config.example.json','README.md','CHANGELOG.md','SKILL.md',
    'sample-preview.html','.gitignore','runtime.ps1','setup.ps1','activate.ps1',
    'install-task.ps1','uninstall-task.ps1','run.ps1','start-setup.cmd',
    'resume-setup.cmd','check.cmd','preview.cmd','status.cmd','uninstall.cmd',
    'tests/test_digest.py','tests/test_regressions.py','tests/test_install.ps1',
    '.github/workflows/test.yml','package_release.py',
]

def build(root, output):
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(root/name,'news-digest-kit/'+name)

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=root/'dist'/'news-digest-kit-share.zip')
    args=parser.parse_args()
    build(root,args.output)
    print('Source-only ZIP created:',args.output)

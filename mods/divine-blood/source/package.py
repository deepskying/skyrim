from pathlib import Path
import zipfile
from catalog import ROOT
def main():
    dst=ROOT/'packaging';dst.mkdir(exist_ok=True)
    path=dst/'DivineBlood-1.0.1.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted((ROOT/'data').rglob('*')):
            if f.is_file():z.write(f,f.relative_to(ROOT/'data'))
        z.write(ROOT/'README.md','README.md')
        z.writestr('meta.ini','[General]\ngameName=Skyrim Special Edition\nversion=1.0.1\nnotes=Divine blood; legacy ESP and records retained.\n')
    print(path)
if __name__=='__main__':main()

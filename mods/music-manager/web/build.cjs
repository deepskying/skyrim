const fs=require('node:fs');const path=require('node:path');
const root=__dirname;fs.mkdirSync(path.join(root,'dist'),{recursive:true});
for(const name of ['index.html','app.js','styles.css'])fs.copyFileSync(path.join(root,name),path.join(root,'dist',name));
console.log('Music Manager UI built (no runtime dependencies).');

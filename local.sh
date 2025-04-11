rm -rf server_agent_project.tar.gz &&
cd .. &&
tar -czvf server_agent_project.tar.gz --exclude='.git' server_agent_project/ &&
cp server_agent_project.tar.gz server_agent_project/ &&
cd server_agent_project &&
git status &&
git add . &&
git commit -m 'updated' &&
git push -u origin master
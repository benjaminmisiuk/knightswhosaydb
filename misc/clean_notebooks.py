#!/usr/bin/env python3
# Clean the notebook cache to save memory online
# Tutorial notebooks are pushed to git lfs!

import os
import subprocess as sub
from tqdm.auto import tqdm

notebooks = []

for r,d,f in os.walk('.'):
  if '.ipynb_checkpoints' in r:
    continue
  if '.pixi' in r:
    continue

  for file in f:
    if file.endswith('.ipynb'):
      notebooks.append(r + '/' + file)

# delete jupyter_nbconvert.log if it exists
if os.path.exists('jupyter_nbconvert.log'):
  os.remove('jupyter_nbconvert.log')

# call jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace on each notebook
# use subprocess instead of os.system
# print stderr output to jupyter_nbconvert.log
prg = tqdm(notebooks, desc='Cleaning notebooks')
for notebook in prg:
  prg.set_postfix_str(notebook)
  sub.run(['jupyter', 'nbconvert', '--ClearOutputPreprocessor.enabled=True', '--inplace', notebook], stderr=open('jupyter_nbconvert.log', 'a'))

print('Cleaned notebooks:')
for notebook in notebooks:
  print(f'  {notebook}')


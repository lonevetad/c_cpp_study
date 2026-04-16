# eval

## to run

### cd

```bash
#!/bin/bash
#from the root folder, i.e. "c_cpp_study"
cd ./src/expr_eval/
```

### build

```bash
#!/bin/bash
g++ -std=c++26 -Wall -Wextra -o expr_eval expr_eval.cpp
```

### run

```bash
#!/bin/bash
rm expr_eval_OUT.txt
./expr_eval >> expr_eval_OUT.txt
```

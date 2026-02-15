***SSH stuff:***



ssh braxton.walk@western.edu@lambda01.wsc.western.edu                                -> login to the lambda server on your account (will ask for password)



scp randofile.c stu414072@lambda01.wsc.western.edu:                                  -> transfer over file to your account (must be outside of lambda environment)



scp randofile.c stu414072@lambda01.wsc.western.edu:/home/stu414072/randofile.c       -> transfer file over to specific location within lambda server



scp -r /blah stu414072@lambda01.wsc.western.edu:                                     -> transfer over entire directory to the lambda server, can also specify location like previous example









***Split screen the terminal: (once in the lambda server)***



tmux                     -> create a terminal environment



Ctrl+b then "            -> splits the terminal into two screens



Ctrl+b + arrow keys      -> select which terminal you are currently on



Ctrl+b + d               -> detach the process so you can close the terminal



Ctrl+b + w               -> select the detached window to view



Ctrl+b + \&               -> close the tmux window (confirm with y)





watch -n 1 'nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv'         -> watch the current gpu usage in an easier to view format














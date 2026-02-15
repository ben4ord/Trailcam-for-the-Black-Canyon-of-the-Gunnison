***YOLOv8 Model Training Commands***



yolo train model=yolov8m.pt data=data.yaml epochs=75 imgsz=640 batch=16                              -> Single device usage



yolo train model=yolov8m.pt data=data.yaml epochs=75 imgsz=640 batch=64 device=0,1,2,3,4,5,6,7       -> Multi-GPU usage (batch size 64 recommended because each GPU will get 64 / 8 = 8 images per batch, if memory allows we can increase to 16-32 images per GPU, just have to test it out, could also decrease to batch size 48 or 32 if memory is an issue with the yolov8x.pt model)



yolo predict model=runs/detect/train2/weights/best.pt source=dataset/images imgsz=640                -> Predict funtion







***Different Models we Could use:***



yolov8n.pt   -> nano model (smallest \& fastest)

yolov8s.pt   -> small model

yolov8m.pt   -> medium model

yolov8l.pt   -> large model

yolov8x.pt   -> extra large model (slowest \& most accurate, only recommended for multiple GPUs)





Dataset size	Recommended model

<5k			s

5k–20k			m

20k–80k			l

80k+ or many classes	x











***Easily grab the latest model from the previous run:***



***Windows:***



Step 1 — Open PowerShell

Press Win + X -> Windows PowerShell.



Save models to a fixed folder (create this folder once) (NOTE: below I outline a different strategy if you want to change the file location of where the Models are saved off to)



mkdir $HOME\\Models





---

---

---



Personally instead of this I had a Capstone\_Project folder in my C: drive with the path: C:\\Capstone\_Project\\Models. I then ran this command in powershell: mkdir "C:\\Capstone\_Project\\Models" -Force



If you take this route, move on to step 2, ignore step 3 and paste this in your profile instead:



function getlatest {

    $dest = "C:\\Capstone\_Project\\Models"

    if (!(Test-Path $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null }



    $remote = ssh stu414072@lambda01.wsc.western.edu "ls -t /home/capstone/runs/detect/\*/weights/best.pt | head -n 1"

    scp "stu414072@lambda01.wsc.western.edu:$remote" "$dest\\"

}



Save \& Close notepad and continue on to step 4. If you want to save it to your %HOME directory, then ignore this step and move on to step 2 (the only difference between this and the original step 3 is the location you want to save the models off to). This command will save the models to this file location: C:\\Capstone\_Project\\Models



---

---

---





Step 2 — Edit your PowerShell profile

Inside PowerShell -> notepad $PROFILE

If it says the file doesn’t exist, choose Yes to create it.





Step 3 — Add this function (NOTE: you will have to change the ssh and scp command to fit your current account - this example is with my account)

function getlatest {

    $remote = ssh stu414072@lambda01.wsc.western.edu "ls -t /home/capstone/runs/detect/\*/weights/best.pt | head -n 1"

    scp "stu414072@lambda01.wsc.western.edu:$remote" "$HOME\\Models\\"

}



Save \& Close notepad





Step 4 — Reload profile

. $PROFILE





Step 5 — Use it

You can now run -> getlatest

It will automatically copy the newest best.pt into your current folder.









***macOS***



Step 1 — Open Terminal

Applications → Utilities → Terminal



Save models to a fixed folder (create this folder once in whatever directory you want them to be saved)

mkdir ~/Models





Step 2 — Check which shell you use

echo $SHELL





Step 3 — Open your shell config file

If using zsh (most likely):

nano ~/.zshrc



If using bash:

nano ~/.bashrc





Step 4 — Add the getlatest shortcut

Paste this at the bottom:

alias getlatest='scp stu414072@lambda01.wsc.western.edu:$(ssh stu414072@lambda01.wsc.western.edu "ls -t /home/capstone/runs/detect/\*/weights/best.pt | head -n 1") ~/Models/'





Step 5 — Save and exit (nano)

Ctrl + O   (save)

Enter

Ctrl + X   (exit)





Step 6 — Reload the shell config

For zsh:

source ~/.zshrc



For bash:

source ~/.bashrc





Step 7 — Use it

getlatest



This command will:

SSH into the server

Find newest best.pt

Copy it into your current Mac directory




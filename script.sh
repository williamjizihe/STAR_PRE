# python3 main.py --env_name AntMaze --max_timesteps 5e3 --eval_freq 1000
# torchrun main.py --env_name AntMaze --max_timesteps 3e6
python3 main.py --env_name AntMaze --max_timesteps 3e6 --boss_update False --boss_continuous True
# python3 main.py --test True --env_name AntMaze
# python3 main.py --env_name AntFall
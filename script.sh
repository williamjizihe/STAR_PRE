# python3 main.py --env_name AntMaze --max_timesteps 5e3 --eval_freq 1000 --llm True --boss_update True
# torchrun main.py --env_name AntFall --max_timesteps 5e6
# python3 main.py --env_name AntMaze --max_timesteps 3e6 --boss_update True
# python3 main.py --test True --env_name AntMaze
# python3 main.py --env_name AntFall
python3 main.py --env_name AntMaze --max_timesteps 7e6 --llm True --boss_update True
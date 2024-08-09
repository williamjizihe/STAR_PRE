# python3 main.py --env_name AntMaze --max_timesteps 1e4 --eval_freq 1000 --llm True --boss_update True --api False
# python3 main.py --env_name AntFall --max_timesteps 5e6 --llm False --boss_update True --api False
python3 main.py --env_name AntMaze --boss_update True --llm True --api False
# python3 main.py --test True --env_name AntMaze --llm True
# python3 main.py --env_name AntFall
# python3 main.py --env_name AntMaze --max_timesteps 5e6 --llm True --boss_update True --api True
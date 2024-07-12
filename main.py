import argparse

from star.train import run_hrac, run_star, run_hiro, run_gara, test_star

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--algo", default="star", type=str)
    parser.add_argument("--mode", default="vanilla", type=str)
    parser.add_argument("--seed", default=2, type=int)
    parser.add_argument("--eval_freq", default=5e3, type=float)
    parser.add_argument("--max_timesteps", default=5e6, type=float)
    parser.add_argument("--save_models", default=True, action="store_true")
    parser.add_argument("--env_name", default="AntFall", type=str)
    parser.add_argument("--loaded_env_name", default=None, type=str)
    parser.add_argument("--load", default=False, type=bool)
    parser.add_argument("--log_dir", default="./logs", type=str)
    parser.add_argument("--no_correction", action="store_true")
    parser.add_argument("--inner_dones", action="store_true")
    parser.add_argument("--absolute_goal", action="store_true")
    parser.add_argument("--binary_int_reward", action="store_true")
    parser.add_argument("--load_adj_net", default=False, action="store_true")
    parser.add_argument("--load_fwd_model", default=False, action="store_true")

    parser.add_argument("--gid", default=0, type=int)
    parser.add_argument("--traj_buffer_size", default=50000, type=int)
    parser.add_argument("--lr_r", default=2e-4, type=float)
    parser.add_argument("--r_margin_pos", default=1.0, type=float)
    parser.add_argument("--r_margin_neg", default=1.2, type=float)
    parser.add_argument("--r_training_epochs", default=25, type=int)
    parser.add_argument("--r_batch_size", default=64, type=int)
    parser.add_argument("--r_hidden_dim", default=128, type=int)
    parser.add_argument("--r_embedding_dim", default=32, type=int)
    parser.add_argument("--goal_loss_coeff", default=20, type=float)
    parser.add_argument("--goal_reward_coeff", default=1, type=float)

    parser.add_argument("--lr_fwd", default=1e-3, type=float)
    parser.add_argument("--fwd_training_epochs", default=3, type=int)
    parser.add_argument("--fwd_batch_size", default=64, type=int)
    parser.add_argument("--fwd_hidden_dim", default=32, type=int)
    parser.add_argument("--fwd_embedding_dim", default=32, type=int)
    
    parser.add_argument("--boss_propose_freq", default=30, type=int) # k 
    parser.add_argument("--train_boss_freq", default=1000, type=int)
    parser.add_argument("--manager_propose_freq", default=10, type=int) # l
    parser.add_argument("--train_manager_freq", default=10, type=int)
    parser.add_argument("--man_discount", default=0.99, type=float)
    parser.add_argument("--ctrl_discount", default=0.95, type=float)

    # Boss Parameters
    parser.add_argument("--boss_batch_size", default=64, type=int)
    parser.add_argument("--boss_buffer_size", default=100000, type=int)
    parser.add_argument("--boss_buffer_min_size", default=5000, type=int)
    parser.add_argument("--boss_policy", default="Q-learning", type=str) # Do not change
    parser.add_argument("--boss_discount_factor", default=0.99, type=float) 
    parser.add_argument("--boss_alpha", default=0.01, type=float) 
    parser.add_argument("--reach_algo", default="Ai2", type=str) # Do not change
    parser.add_argument("--boss_eps", default=0.99, type=int)
    parser.add_argument("--boss_eps_min", default=0.01, type=int)
    parser.add_argument("--boss_eps_decay", default=0.99995, type=float)
    parser.add_argument("--boss_eps_linear_decay", default=1e-6, type=float)
    parser.add_argument("--boss_continuous", default=False, type=bool)
    parser.add_argument("--boss_update", default=True, type=bool)
    
    # Manager Parameters
    parser.add_argument("--man_soft_sync_rate", default=0.005, type=float)
    parser.add_argument("--man_batch_size", default=128, type=int)
    parser.add_argument("--man_buffer_size", default=2e5, type=int)
    parser.add_argument("--man_rew_scale", default=0.1, type=float)
    parser.add_argument("--man_act_lr", default=1e-4, type=float)
    parser.add_argument("--man_crit_lr", default=1e-3, type=float)
    parser.add_argument("--candidate_goals", default=10, type=int)
    parser.add_argument("--man_continuous", default=False, type=bool)
    
    # Controller Parameters
    parser.add_argument("--ctrl_soft_sync_rate", default=0.005, type=float)
    parser.add_argument("--ctrl_batch_size", default=128, type=int)
    parser.add_argument("--ctrl_buffer_size", default=2e5, type=int)
    parser.add_argument("--ctrl_rew_scale", default=1.0, type=float)
    parser.add_argument("--ctrl_act_lr", default=1e-4, type=float)
    parser.add_argument("--ctrl_crit_lr", default=1e-3, type=float)
    parser.add_argument("--ctrl_continuous", default=False, type=bool)
    
    # Noise Parameters
    parser.add_argument("--noise_type", default="normal", type=str)
    parser.add_argument("--ctrl_noise_sigma", default=1., type=float)
    parser.add_argument("--man_noise_sigma", default=1., type=float)

    # Reachability Parameters
    parser.add_argument("--tau1", default="0.7", type=float)
    parser.add_argument("--tau2", default="0.01", type=float)

    # Experiment Number
    parser.add_argument("--exp", default="0", type=str)
    
    # Test Parameters
    parser.add_argument("--test", default=False, type=bool)

    # Run the algorithm
    args = parser.parse_args()
    args.boss_update = False # This line needs to be removed
    
    if args.env_name in ["AntGather", "AntMazeSparse"]:
        args.man_rew_scale = 1.0
        if args.env_name == "AntGather":
            args.inner_dones = True
    
    if args.env_name == "AntFall":
        args.boss_alpha = 0.005

    print('=' * 30)
    for key, val in vars(args).items():
        print('{}: {}'.format(key, val))

    def run(args):
        if args.test:
            print("-----------Testing-----------")
            test_star(args)
        elif args.algo == "hrac":
            run_hrac(args)
        elif args.algo == "star":
            run_star(args)
        elif args.algo == "hiro":
            run_hiro(args)
        elif args.algo == "gara":
            run_gara(args)
    
    ### Standard Experiments
    if args.mode == 'vanilla':
        for exp in range(1):
            args.exp = str(exp)
            run(args)
            
    ### Transfer Learning Experiments
    if args.mode == 'transfer':
        for exp in range(5):
            # Train on 2 Rooms
            args.exp = 'vanilla' + str(exp)
            run_star(args)
        
            # Train on 3 Rooms
            args.exp = 'vanilla' + str(exp)
            args.env_name = "3Rooms"
            run(args)
            # Transfer on 3 Rooms
            args.exp = 'transfer' + str(exp)
            args.load = True
            args.loaded_env_name = "2Rooms"
            args.load_fwd_model = True
            run(args)

            # Train on 4 Rooms
            args.exp = 'vanilla' + str(exp)
            args.env_name = "4Rooms"
            run(args)
            # Transfer on 4 Rooms
            args.exp = 'transfer' + str(exp)
            args.load = True
            args.loaded_env_name = "2Rooms"
            args.load_fwd_model = True
            run(args)
import torch
import torch.nn as nn
import time
from typing import Optional

class ColumnParallelLinear(nn.Module):
    def __init__(self, in_features, out_features, bias=True, gather_output=True, init_method=None):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features, bias=bias)
        if init_method:
            self.linear.weight.data = init_method(self.linear.weight.data)

    def forward(self, x):
        return self.linear(x)

class RowParallelLinear(nn.Module):
    def __init__(self, in_features, out_features, bias=True, input_is_parallel=True, init_method=None):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features, bias=bias)
        if init_method:
            self.linear.weight.data = init_method(self.linear.weight.data)

    def forward(self, x):
        return self.linear(x)

class FeedForward(nn.Module):
    def __init__(self, dim: int, hidden_dim: int, multiple_of: int, ffn_dim_multiplier: Optional[float]):
        super().__init__()
        hidden_dim = int(2 * hidden_dim / 3)
        # custom dim factor multiplier
        if ffn_dim_multiplier is not None:
            hidden_dim = int(ffn_dim_multiplier * hidden_dim)
        hidden_dim = multiple_of * ((hidden_dim + multiple_of - 1) // multiple_of)

        self.w1 = ColumnParallelLinear(dim, hidden_dim, bias=False, gather_output=False, init_method=lambda x: x)
        self.w2 = RowParallelLinear(hidden_dim, dim, bias=False, input_is_parallel=True, init_method=lambda x: x)
        self.w3 = ColumnParallelLinear(dim, hidden_dim, bias=False, gather_output=False, init_method=lambda x: x)

    def forward(self, x):
        x = self.w1(x)
        x = self.w2(x)
        x = self.w3(x)
        return x

# Define dimensions
dim = 512
hidden_dim = 2048
multiple_of = 256
ffn_dim_multiplier = 1.0

# Create layers
feedforward_parallel = FeedForward(dim, hidden_dim, multiple_of, ffn_dim_multiplier)
feedforward_normal = nn.Sequential(
    nn.Linear(dim, hidden_dim, bias=False),
    nn.Linear(hidden_dim, dim, bias=False),
    nn.Linear(dim, hidden_dim, bias=False)
)

# Create input tensor
input_tensor = torch.randn(1024, dim)

# Measure time for parallel feedforward
start_time = time.time()
output_parallel = feedforward_parallel(input_tensor)
end_time = time.time()
parallel_time = end_time - start_time

# Measure time for normal feedforward
start_time = time.time()
output_normal = feedforward_normal(input_tensor)
end_time = time.time()
normal_time = end_time - start_time

print(f"Parallel FeedForward Time: {parallel_time:.6f} seconds")
print(f"Normal FeedForward Time: {normal_time:.6f} seconds")

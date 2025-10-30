import torch 
print(torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA device count:", torch.cuda.device_count())
print("CUDA device name:", torch.cuda.get_device_name(0))
print("CUDA device properties:", torch.cuda.get_device_properties(0))
print("Current CUDA device:", torch.cuda.current_device())
print("CUDA memory allocated:", torch.cuda.memory_allocated(0))
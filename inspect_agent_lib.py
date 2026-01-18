from agents import Agent, Runner
import inspect

print("Agent analysis:")
print(dir(Agent))
print("-" * 20)
print("Runner analysis:")
print(dir(Runner))
print("-" * 20)

try:
    print("Runner.run signature:")
    print(inspect.signature(Runner.run))
except:
    pass

import asyncio
from agents import Runner

async def inspect_runner():
    print(f"Runner methods: {[m for m in dir(Runner) if not m.startswith('_')]}")
    if hasattr(Runner, 'run'):
        import inspect
        is_async = inspect.iscoroutinefunction(Runner.run)
        print(f"Runner.run is async: {is_async}")
    else:
        print("Runner has no 'run' method")

if __name__ == "__main__":
    asyncio.run(inspect_runner())

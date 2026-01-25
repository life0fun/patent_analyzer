from app.subag  ents.master_agent import MasterAgent

def main():
    agent = MasterAgent()

    # Claim A: A drone with specific features
    claim_a = """
    1. A method for controlling an unmanned aerial vehicle (UAV), comprising:
    receiving a first signal from a remote controller;
    identifying a target location based on the first signal;
    calculating a flight path to the target location; and
    actuating a motor to propel the UAV along the flight path.
    """

    # Claim B: Similar but with added obstacle avoidance
    claim_b = """
    1. A method for operating a drone, comprising:
    receiving a command signal from a user device;
    determining a destination based on the command signal;
    detecting an obstacle in a projected path;
    computing an alternative route to the destination; and
    controlling a propulsion system to move the drone along the alternative route.
    """

    print("Analyzing Claims...")
    report = agent.analyze(claim_a, claim_b)
    print("\n" + "="*40 + "\n")
    print(report)
    print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    main()

import logging
from strands import Agent
#TODO: import python_repl, file_write
from strands_tools import python_repl
from strands_tools import file_write




#TODO: Enable Strands debug log level

# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.DEBUG)

# Add a handler to see the logs
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)





# Your magical creation here
arcane_scribe = Agent(
    #tools= #TODO: add the tools
    tools=[
        python_repl,    #tools for executing python code
        file_write      #tools for writing files
    ],
    system_prompt="""You are Kiro the Grey Hat, a wizard who specializes in the ancient art of code magic. 
    When asked to create spells (code), you inscribe them on parchment (files) and then cast (execute) them to demonstrate their power."""
)

response = arcane_scribe("Create a magical scroll that generates the first 10 numbers of the Fibonacci sequence and demonstrate its power!")
print(response)


# dans le terminal (a remettre a chaque nouveau terminal car ve)
# export BYPASS_TOOL_CONSENT=true

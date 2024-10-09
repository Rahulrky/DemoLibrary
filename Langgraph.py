import os
import uuid
import configparser
from typing import Annotated, List

from typing_extensions import TypedDict

from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import AnyMessage, ToolMessage, add_messages
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import tool
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt.tool_node import ToolNode, tools_condition


class TextToSQLAgent:
    """
    A text-to-SQL agent that uses LangChain and LangGraph to generate SQL queries from natural language questions.
    """

    def __init__(
        self,
        db_uri: str,
        api_key: str,
        model_name: str = "gpt-4",
        temperature: float = 0.0,
    ):
        """
        Initialize the TextToSQLAgent.

        Args:
            db_uri (str): The URI of the SQLite database.
            api_key (str): The OpenAI API key.
            model_name (str, optional): The name of the OpenAI model to use. Defaults to "gpt-4".
            temperature (float, optional): The temperature to use for the LLM. Defaults to 0.0.
        """
        # Set API key
        os.environ["OPENAI_API_KEY"] = api_key

        # Initialize database connection
        self.db = SQLDatabase.from_uri(db_uri)
        print(self.db.dialect)
        print(self.db.get_usable_table_names())
        self.db.run("SELECT * FROM Artist LIMIT 10;")

        # Initialize LLM
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)

        # Initialize tools
        self.tools = []
        self._setup_tools()

        # Initialize assistant
        self.assistant_runnable = self._setup_assistant()

        # Initialize graph
        self.graph = self._setup_graph()

    def _setup_tools(self):
        """
        Set up the tools for the agent, including the SQL toolkit and custom tools for query checking and result checking.
        """
        # SQL toolkit
        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
        self.tools = toolkit.get_tools()

        # Query checking tool
        query_check_system = """You are a SQL expert with a strong attention to detail.
Double check the SQLite query for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

Execute the correct query with the appropriate tool."""
        query_check_prompt = ChatPromptTemplate.from_messages(
            [("system", query_check_system), ("user", "{query}")]
        )
        query_check = query_check_prompt | self.llm

        @tool
        def check_query_tool(query: str) -> str:
            """
            Use this tool to double check if your query is correct before executing it.

            Args:
                query (str): The SQL query to check.

            Returns:
                str: The checked (and possibly corrected) SQL query.
            """
            return query_check.invoke({"query": query}).content

        # Query result checking tool
        query_result_check_system = """You are grading the result of a SQL query from a DB.
- Check that the result is not empty.
- If it is empty, instruct the system to re-try!"""
        query_result_check_prompt = ChatPromptTemplate.from_messages(
            [("system", query_result_check_system), ("user", "{query_result}")]
        )
        query_result_check = query_result_check_prompt | self.llm

        @tool
        def check_result_tool(query_result: str) -> str:
            """
            Use this tool to check the query result from the database to confirm it is not empty and is relevant.

            Args:
                query_result (str): The result of the SQL query.

            Returns:
                str: A message indicating whether the result is acceptable.
            """
            return query_result_check.invoke({"query_result": query_result}).content

        # Add custom tools to the tools list
        self.tools.append(check_query_tool)
        self.tools.append(check_result_tool)

    def _setup_assistant(self) -> Runnable:
        """
        Set up the assistant runnable.

        Returns:
            Runnable: The assistant runnable.
        """
        query_gen_system = """
ROLE:
You are an agent designed to interact with a SQL database. You have access to tools for interacting with the database.
GOAL:
Given an input question, create a syntactically correct SQLite query to run, then look at the results of the query and return the answer.
INSTRUCTIONS:
- Only use the below tools for the following operations.
- Only use the information returned by the below tools to construct your final answer.
- To start you should ALWAYS look at the tables in the database to see what you can query. Do NOT skip this step.
- Then you should query the schema of the most relevant tables.
- Write your query based upon the schema of the tables. You MUST double check your query before executing it.
- Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
- You can order the results by a relevant column to return the most interesting examples in the database.
- Never query for all the columns from a specific table, only ask for the relevant columns given the question.
- If you get an error while executing a query, rewrite the query and try again.
- If the query returns a result, use check_result tool to check the query result.
- If the query result result is empty, think about the table schema, rewrite the query, and try again.
- DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database."""

        query_gen_prompt = ChatPromptTemplate.from_messages(
            [("system", query_gen_system), ("placeholder", "{messages}")]
        )

        assistant_runnable = query_gen_prompt | self.llm.bind_tools(self.tools)

        return assistant_runnable

    def _setup_graph(self) -> StateGraph:
        """
        Set up the graph for the agent.

        Returns:
            StateGraph: The compiled state graph.
        """

        class State(TypedDict):
            messages: Annotated[List[AnyMessage], add_messages]

        class Assistant:
            def __init__(self, runnable: Runnable):
                self.runnable = runnable

            def __call__(self, state: State, config: RunnableConfig):
                while True:
                    # Append to state
                    state = {**state}
                    # Invoke the tool-calling LLM
                    result = self.runnable.invoke(state)
                    # If it is a tool call -> response is valid
                    # If it has meaningful text -> response is valid
                    # Otherwise, we re-prompt it because response is not meaningful
                    if not result.tool_calls and (
                        not result.content
                        or isinstance(result.content, list)
                        and not result.content[0].get("text")
                    ):
                        messages = state["messages"] + [
                            ("user", "Respond with a real output.")
                        ]
                        state = {**state, "messages": messages}
                    else:
                        break
                return {"messages": result}

        def create_tool_node_with_fallback(tools: list) -> dict:
            return ToolNode(tools).with_fallbacks(
                [RunnableLambda(handle_tool_error)], exception_key="error"
            )

        def handle_tool_error(state) -> dict:
            error = state.get("error")
            tool_calls = state["messages"][-1].tool_calls
            return {
                "messages": [
                    ToolMessage(
                        content=f"Error: {repr(error)}\n please fix your mistakes.",
                        tool_call_id=tc["id"],
                    )
                    for tc in tool_calls
                ]
            }

        # Build the graph
        builder = StateGraph(State)

        # Define nodes
        builder.add_node("assistant", Assistant(self.assistant_runnable))
        builder.add_node("tools", create_tool_node_with_fallback(self.tools))

        # Define edges
        builder.set_entry_point("assistant")
        builder.add_conditional_edges(
            "assistant",
            tools_condition,
            {"tools": "tools", END: END},
        )
        builder.add_edge("tools", "assistant")

        # The checkpointer lets the graph persist its state
        memory = SqliteSaver.from_conn_string(":memory:")
        graph = builder.compile(checkpointer=memory)

        return graph

    def run_query(self, question: str) -> str:
        """
        Run a natural language question through the agent and return the answer.

        Args:
            question (str): The natural language question.

        Returns:
            str: The answer from the agent.
        """
        # Generate a unique thread ID
        thread_id = str(uuid.uuid4())

        # Config for the graph
        config = {
            "configurable": {
                # Checkpoints are accessed by thread_id
                "thread_id": thread_id,
            }
        }

        # Prepare the initial message
        msg = {"messages": ("user", question)}
        # Invoke the graph
        result = self.graph.invoke(msg, config)
        # Extract the assistant's response
        assistant_message = result["messages"][-1].content

        return assistant_message


if __name__ == "__main__":
    import sys

    # Read configuration from config.ini
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Fetch configuration parameters
    try:
        db_uri = config.get("Settings", "db_uri")
        api_key = config.get("Settings", "api_key")
        model_name = config.get("Settings", "model_name")
        temperature = config.getfloat("Settings", "temperature")
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize the agent
    agent = TextToSQLAgent(
        db_uri=db_uri,
        api_key=api_key,
        model_name=model_name,
        temperature=temperature,
    )

    # List of questions
    questions = [
        "Which country's customers spent the most? And how much did they spend?",
        "How many albums does the artist Led Zeppelin have?",
        "What was the most purchased track of 2017?",
        "Which sales agent made the most in sales in 2009?",
    ]

    # Run each question through the agent
    for question in questions:
        print(f"Question: {question}")
        answer = agent.run_query(question)
        print(f"Answer: {answer}")
        print("-" * 50)

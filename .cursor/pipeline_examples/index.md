- agents_produce_agents.yaml:
    description: personalised slack reporting fetching data from warehouse, passing to prompt, sending to messaging destination
    variations: could fetch data from any warehouse e.g. postgres, bigquery, databricks etc. 
    messaging_variations: could send data to any destination
    prompt_variations: could do any other prompt, could use a different task from Orchestra
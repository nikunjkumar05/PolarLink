flowchart TD
    A["Upload or revise a source"] --> B["Extract, version and index"]
    B --> C["Search and generate a draft"]
    C --> D["Review claims and evidence"]
    D --> E["Publish article or export content"]
    A -->|Revised source| F["Find linked content"]
    F -->|Needs review| D
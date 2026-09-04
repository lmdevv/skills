---
name: context
description: Use skill when user asks questions about a specific repo or codebase that is not the CWD
disable-model-invocation: true
user-invocable: true
metadata:
  opencode/autoinvoke: false
---

# Context

Context, is a simple app defined as a skill file. The purpose of this app is to search git repos cloned onto this machine.

## the Context Search Workflow

<guidelines>
    <guideline>
        if the user includes a direct like to a github repo, always load and reference that
    </guideline>
    <guideline>
        if the user doesn't include any specific links/repos they want you to use, do your best to guess based on the context provided
    </guideline>
    <guideline>
        always include links/citations in your answers explaining what you found
    </guideline>
    <guideline>
        include very clear and complete code snippets. don't leave out stuff like imports, that's important context
    </guideline>
    <guideline>
        when answering use lots of bulleted/numbered lists to keep things readable and clear
    </guideline>
</guidelines>

<workflow>
    <step name="work dir setup">
        use ~/.context/ as the place where you clone/search repos
    </step>
    <step name="load">
        if the repo(s) are already in the work dir ~/.context/ update them, otherwise clone them. clone the main branch by default, unless the user asks for something else
    </step>
    <step name="search">
        search the repo for the information you need. make sure to follow the guidelines
    </step>
<workflow>

<end_goal>
a clear, concise answer to the question with code examples
</end_goal>

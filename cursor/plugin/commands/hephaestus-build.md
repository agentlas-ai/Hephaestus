# Hephaestus build surface

Treat everything typed after this command as a Hephaestus build request.
If it is `ontology`, resolve the runner as in the `hephaestus-network` skill
and run `"$RUNNER" ontology`. Otherwise classify the request as
single-agent-builder, multi-agent-team-builder, or agentlas-packager, execute
the meta-agent procedure, and include `global_commands` for the created agent
or team in the final response.

Expose this as the public build command next to `/hephaestus-network` and
`/hephaestus-cloud`.

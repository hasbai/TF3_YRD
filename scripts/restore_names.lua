(function()
  local targets = { {{INDUSTRIES}} }
  local C = api.type.ComponentType
  local candidates = {}
  api.engine.forEachEntityWithComponent(function(entity)
    local industry = api.engine.getComponent(entity, C.INDUSTRY)
    local con = api.engine.getComponent(industry.construction, C.CONSTRUCTION)
    if con then
      local p = con.transf:getTransl()
      candidates[#candidates + 1] = { entity = entity, fileName = con.fileName, x = p.x, y = p.y }
    end
  end, C.INDUSTRY)
  local jobs, used = {}, {}
  for _, target in ipairs(targets) do
    local matches = {}
    for _, candidate in ipairs(candidates) do
      local dx, dy = candidate.x - target.x, candidate.y - target.y
      if candidate.fileName == target.fileName and dx * dx + dy * dy <= 120 * 120 then
        matches[#matches + 1] = candidate
      end
    end
    assert(#matches == 1, target.name .. ": expected one matching industry, found " .. #matches)
    local match = matches[1]
    assert(not used[match.entity], target.name .. ": duplicate industry match")
    used[match.entity] = true
    if api.engine.util.getEntityName(match.entity) ~= target.name then
      jobs[#jobs + 1] = { entity = match.entity, name = target.name }
    end
  end
  local pending, succeeded, failed = #jobs, 0, 0
  if pending == 0 then
    print("YRD: all " .. #targets .. " industry names already match")
    return
  end
  for _, job in ipairs(jobs) do
    api.cmd.sendCommand(api.cmd.makeEntitySetNameCmd(job.entity, job.name), function(_, success)
      if success then succeeded = succeeded + 1 else failed = failed + 1 end
      pending = pending - 1
      if pending == 0 then
        print("YRD: renamed " .. succeeded .. ", failed " .. failed .. ", already correct " .. (#targets - #jobs))
      end
    end)
  end
end)()

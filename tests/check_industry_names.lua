local command, fixture = arg[1], dofile(arg[2])
local C = { INDUSTRY = 1, CONSTRUCTION = 2 }
local entities, jobs, callbacks, names
local function reset()
  entities, jobs, callbacks, names = {}, {}, {}, {}
  for i, target in ipairs(fixture) do
    entities[i] = { construction = 1000 + i }
    entities[1000 + i] = {
      fileName = target.fileName,
      transf = { getTransl = function() return { x = target.x + 1, y = target.y } end },
    }
    names[i] = "random industry " .. i
  end
  api = {
    type = { ComponentType = C },
    engine = {
      forEachEntityWithComponent = function(fn, component)
        assert(component == C.INDUSTRY)
        for i = 1, #fixture do fn(i) end
        if entities[999] then fn(999) end
      end,
      getComponent = function(id) return entities[id] end,
      util = { getEntityName = function(id) return names[id] end },
    },
    cmd = {
      makeEntitySetNameCmd = function(id, name) return { id = id, name = name } end,
      sendCommand = function(job, callback)
        jobs[#jobs + 1], callbacks[#callbacks + 1] = job, callback
      end,
    },
  }
end

reset()
dofile(command)
assert(#jobs == #fixture)
for i, job in ipairs(jobs) do
  assert(job.id == i and job.name == fixture[i].name)
  names[job.id] = job.name
  callbacks[i](nil, true)
end
jobs = {}
dofile(command)
assert(#jobs == 0, "Repeat execution must preserve already correct names")

reset()
entities[1000 + #fixture].fileName = "::/industries/wrong/wrong.con"
assert(not pcall(dofile, command) and #jobs == 0, "Wrong type must abort before any rename")

reset()
entities[1001].transf.getTransl = function() return { x = fixture[1].x + 121, y = fixture[1].y } end
assert(not pcall(dofile, command) and #jobs == 0, "Wrong position must abort before any rename")

reset()
entities[999] = { construction = 1001 }
assert(not pcall(dofile, command) and #jobs == 0, "Ambiguous position must abort before any rename")

reset()
local realPrint, message = print, nil
print = function(value) message = value end
dofile(command)
assert(message == nil, "Must wait for asynchronous command results")
for i, callback in ipairs(callbacks) do callback(nil, i ~= 1) end
print = realPrint
assert(message == "YRD: renamed " .. (#fixture - 1) .. ", failed 1, already correct 0")
print("Industry rename: names, repeat execution, type/position/ambiguity and asynchronous failures passed")

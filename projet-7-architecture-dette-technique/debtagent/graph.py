"""Module dependencies: layer rules, cycles, and coupling.

Instability is Martin's metric I = Ce / (Ca + Ce), where Ca (fan-in) counts the
internal modules that depend on a module and Ce (fan-out) the internal modules
it depends on. Cycles are the strongly connected components of the import
graph (Tarjan, 1972) that contain more than one module.
"""


def layer_of(module, layers):
    best, length = None, -1
    for layer, prefixes in layers.items():
        for p in prefixes:
            if (module == p or module.startswith(p + ".")) and len(p) > length:
                best, length = layer, len(p)
    return best


def cycles(nodes, edges):
    graph = {n: sorted({t for s, t in edges if s == n}) for n in nodes}
    index, low, stack, on_stack, result, counter = {}, {}, [], set(), [], [0]

    def strong(v):  # iterative Tarjan, so that deep graphs do not overflow the stack
        work = [(v, iter(graph[v]))]
        index[v] = low[v] = counter[0]; counter[0] += 1
        stack.append(v); on_stack.add(v)
        while work:
            node, children = work[-1]
            for w in children:
                if w not in index:
                    index[w] = low[w] = counter[0]; counter[0] += 1
                    stack.append(w); on_stack.add(w)
                    work.append((w, iter(graph[w])))
                    break
                if w in on_stack:
                    low[node] = min(low[node], index[w])
            else:
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[node])
                if low[node] == index[node]:
                    component = []
                    while True:
                        w = stack.pop(); on_stack.discard(w); component.append(w)
                        if w == node:
                            break
                    if len(component) > 1:
                        result.append(sorted(component))

    for n in sorted(nodes):
        if n not in index:
            strong(n)
    return sorted(result)


def layer_violations(dependencies, layers, allowed):
    found = []
    for d in dependencies:
        a, b = layer_of(d.source, layers), layer_of(d.target, layers)
        if a and b and a != b and b not in allowed.get(a, []):
            found.append((d, a, b))
    return found


def coupling(nodes, edges):
    fan_in = {n: 0 for n in nodes}
    fan_out = {n: 0 for n in nodes}
    for s, t in set(edges):
        fan_out[s] += 1
        fan_in[t] += 1
    return {n: (fan_in[n], fan_out[n], round(fan_out[n] / (fan_in[n] + fan_out[n]), 2) if fan_in[n] + fan_out[n] else 0.0)
            for n in nodes}

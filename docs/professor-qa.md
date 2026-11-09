# CyberGuard — Professor Questions and Answers

These are likely questions and short answers. Each answer is easy to say out loud.
Keep answers to a few simple sentences.

---

### 1. What is Suricata?

Suricata is a network IDS. It reads network traffic and checks it against rules.
When a rule matches, it writes an alert. It is free and open source.

### 2. What is an IDS?

IDS means Intrusion Detection System. It watches traffic and warns about
suspicious things. It only detects and alerts. It does not block.

### 3. What is the difference between IDS and IPS?

An IDS only watches and warns. An IPS (Intrusion Prevention System) can also block
the bad traffic. Our project is IDS only. It detects but never blocks.

### 4. Why did you choose IDS and not IPS?

Our goal is to monitor and learn, not to block real users. IPS can drop good
traffic by mistake. IDS is safer for a lab and keeps the focus on detection.

### 5. What is EVE JSON?

EVE JSON is Suricata's output format. It is a text file with one JSON object per
line. Each line is one event, like an alert or a stats record. We read only the
alert lines.

### 6. Why does Python not detect anything?

Detection is Suricata's job. If Python also guessed attacks, the results would not
be trustworthy. We keep one engine so the system stays clear and honest. Python
only reads, stores, and shows the alerts.

### 7. How do you prove the detection is real?

We run the rule toggle experiment. First we turn off rule 1000001 and the alert
stops. Then we turn it back on and the alert returns. This shows Suricata does the
detection, not Python.

### 8. Can you explain your first rule, line by line?

The rule is:
`alert http any any -> any any (msg:"CyberGuard Test Alert"; flow:to_server,established; http.uri; content:"/cyberguard-test"; priority:1; classtype:misc-activity; sid:1000001; rev:2;)`

- `alert` is the action: write an alert when it matches.
- `http` is the protocol: this rule looks at HTTP traffic.
- `any any -> any any` means any source and any destination (IP and port).
- `flow:to_server,established` means a real client-to-server request.
- `http.uri; content:"/cyberguard-test"` means the URL must contain that text.
- `priority:1` sets a high priority, which gives severity 1.
- `classtype:misc-activity` is the category.
- `sid:1000001` is the rule id. `rev:2` is the rule version.

### 9. What is different in your second rule?

The second rule is almost the same. It matches `/cyberguard-warning` instead. Its
id is `sid:1000002`. Its `priority:2` gives severity 2. So it is a bit less serious
than the first rule.

### 10. What does `flow:to_server,established` mean?

`to_server` means the traffic goes from the client to the server. `established`
means the TCP connection is already set up. Together they match a normal request,
not random or half-open packets.

### 11. What is a SID?

SID means Signature ID. It is the unique number of a rule. We use numbers from
1000000 and up. This range is free for local rules and does not clash with vendor
rules.

### 12. What is `rev` in a rule?

`rev` is the revision number of the rule. We raise it when we change the rule. We
changed our rules from rev 1 to rev 2 when we added priority and class.

### 13. What is severity and how does priority set it?

Severity shows how serious an alert is. 1 is the most serious. In Suricata, a
`priority:1` rule produces a severity 1 alert. So priority in the rule controls the
severity in the alert.

### 14. What is `classtype`?

`classtype` is the class or category of the alert. It groups similar alerts. We use
`misc-activity`, which is a simple general class for lab activity.

### 15. What is a PCAP?

PCAP is a saved file of captured packets. Suricata can read a PCAP file offline, or
read live traffic. Both give the same kind of alerts. We mostly use live loopback
traffic.

### 16. What is HOME_NET?

HOME_NET is a Suricata setting. It tells Suricata which IP addresses are "our"
network. Rules can use it to focus on inside or outside traffic. Our two rules use
`any`, so they do not depend on HOME_NET.

### 17. Why do you capture on loopback (`lo`)?

Our lab traffic is local: the test server and the client are on the same machine.
That traffic goes over the loopback interface. So we tell Suricata to watch `lo`.
This keeps the lab simple and safe.

### 18. Why not watch the real network interface?

Watching the real interface (for example `eth0`) is possible. But it adds noise and
some setup. For a clear demo, loopback is enough. Using a real interface is listed
as future work.

### 19. How do you avoid storing the same alert twice?

We use two safety nets. First, the reader saves a byte offset, so it does not read
old lines again. Second, the database has a UNIQUE rule on flow id, raw time, and
SID. So even a repeated line is stored only once.

### 20. What happens if the EVE file is rotated or truncated?

If the file is replaced, its inode changes, and the reader starts from the
beginning of the new file. If the file gets shorter, the reader also restarts from
zero. If the file is missing, the reader returns a clear "missing" state and does
not crash.

### 21. Why did you use SQLite?

SQLite is a single file database. It needs no server and no setup. It is perfect
for a small project. If we delete the file, the app rebuilds it from the alerts.

### 22. What is a false positive and a false negative?

A false positive is an alert for traffic that is actually safe. A false negative is
a real attack that got no alert. Good rules try to reduce both. Our rules are
simple test rules, so they match exactly what we send.

### 23. How is the dashboard safe from XSS?

XSS is when bad text becomes code in the page. We never put alert data into raw
HTML. We use `textContent`, which shows text as plain text. So a crafted URL in an
alert cannot run as code.

### 24. Can the dashboard run commands on the server?

No. No API route runs shell commands. No route takes a file path from the request.
The rules file path is fixed in the settings. So the web app cannot be used to run
commands or read random files.

### 25. How does the Telegram feature work and stay safe?

If you set a token and chat id, Python sends a short message for each new serious
alert. It uses plain text, so a bad URL cannot inject formatting. Any network error
is caught and never crashes the reader. The token stays only in a local `.env`.

### 26. Does Telegram send old alerts when it starts?

No. The first read cycle is a quiet baseline. It records the alerts already in the
file but sends nothing. So starting the app does not flood you with old alerts.
Only new alerts after that trigger a message.

### 27. What are the main limitations of the project?

It watches loopback only. It has just two rules. It is IDS only, so it does not
block. The rate-limit summary and token revocation are only tested with mock tests.
It uses the Flask dev server and has no login.

### 28. What would you add next?

More and better rules, maybe with `suricata-update` for community rules. Capture on
a real interface. Add a login to the dashboard. Package it with Docker for easy
setup. These are all future work.

### 29. What is `suricata-update`?

`suricata-update` is a tool that downloads rule sets from the community. It helps
you get many ready-made rules. We did not use it here because we wanted a small,
clear set of our own rules.

### 30. What did each phase do?

Phase 0 set up the repo and rules of work. Phase 1 built the Python app shell.
Phase 2 installed and set up Suricata. Phase 3 tested real detections. Phase 4
connected the backend to real EVE JSON. Phase 5 built the dashboard. Phase 6 added
the Rule Lab and the test scripts. Phase 7 added optional Telegram. Phase 8 is the
documentation and this presentation.

### 31. Why should we trust your status screen?

Because it checks the real process. It reads the pidfile and the process name under
`/proc`. It never says "running" just because a log file exists. If it cannot
check, it says "unverified" instead of guessing.

### 32. How many automated tests do you have?

We have 57 tests. They run on Windows with no Suricata and no network. They cover
reading, storing, dedup, the API, the rules parser, and the Telegram logic with a
mocked sender.

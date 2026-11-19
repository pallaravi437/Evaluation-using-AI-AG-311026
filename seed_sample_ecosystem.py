import os
import sys
import uuid
from datetime import datetime, timezone, date

# Ensure root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from services.lecturer_service import LecturerService
from services.student_service import StudentService
from services.assessment_service import AssessmentService
from services.submission_service import SubmissionService

app = None


SEED_DATA = [
    {
        "lecturer": {
            "full_name": "Dr. Ramesh Sharma",
            "username": "dr_ramesh",
            "email": "ramesh.sharma@college.edu",
            "password": "Ramesh@123",
            "subject": "Basic Electronics & Amplifiers",
            "mobile": "9848011221",
            "specialization": "Analog VLSI & Electronic Devices"
        },
        "department": "ECE",
        "semester": "Semester 1",
        "section": "A",
        "students": [
            {"name": "KASHABOINA PRANAVI", "pin": "26054-BEA-001", "phone": "9502210435"},
            {"name": "A SUJATHA", "pin": "26054-BEA-002", "phone": "6305307638"},
            {"name": "BADAVATH ROHITH RAJ", "pin": "26054-BEA-003", "phone": "8522878783"},
            {"name": "LOLABHATTU SAI SATWIK", "pin": "26054-BEA-004", "phone": "9866100836"},
            {"name": "CHINTA SHIVANI", "pin": "26054-BEA-005", "phone": "9848022334"}
        ],
        "assessments": [
            {
                "title": "Unit 1: BJT Characteristics & CE Configuration",
                "type": "slip_test",
                "max_marks": 20.0,
                "pass_percentage": 40.0,
                "instructions": "Draw neat Common Emitter circuit diagram with proper biasing and derive the relationship between Alpha and Beta.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "Draw the circuit diagram of an NPN transistor in Common Emitter (CE) configuration with input and output biasing. Explain its input and output characteristics.",
                        "max_marks": 10.0,
                        "model_answer": "Circuit consists of NPN BJT with base-emitter forward biased by VBB and collector-emitter reverse biased by VCC. Input characteristics plot IB vs VBE at constant VCE. Output characteristics plot IC vs VCE at constant IB, showing cutoff, active, and saturation regions.",
                        "criteria": [
                            {"criterion_name": "Circuit Schematic & Biasing", "max_marks": 4.0, "guidance": "Correct VBB, VCC polarities, resistor placements, and NPN arrow pointing outward at emitter."},
                            {"criterion_name": "Input Characteristics Curve", "max_marks": 3.0, "guidance": "IB vs VBE graph showing knee voltage around 0.7V for Silicon."},
                            {"criterion_name": "Output Characteristic Regions", "max_marks": 3.0, "guidance": "Identification of active, saturation, and cutoff regions with dynamic resistance formula."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_type": "subjective",
                        "question_text": "Derive the mathematical relationship between common base current gain (Alpha) and common emitter current gain (Beta). If Alpha = 0.985, calculate Beta.",
                        "max_marks": 10.0,
                        "model_answer": "Starting with IE = IB + IC and dividing by IC yields 1/alpha = (1/beta) + 1, therefore beta = alpha / (1 - alpha). For alpha = 0.985, beta = 0.985 / (1 - 0.985) = 0.985 / 0.015 = 65.67.",
                        "criteria": [
                            {"criterion_name": "Basic Current Equation", "max_marks": 3.0, "guidance": "IE = IB + IC correctly stated and substituted with alpha and beta definitions."},
                            {"criterion_name": "Algebraic Derivation", "max_marks": 4.0, "guidance": "Clear step-by-step rearrangement to reach beta = alpha / (1 - alpha)."},
                            {"criterion_name": "Numerical Calculation", "max_marks": 3.0, "guidance": "Accurate calculation beta = 65.67."}
                        ]
                    }
                ]
            },
            {
                "title": "Unit 2: Semiconductor Diodes & Rectifiers MCQ",
                "type": "mcq_test",
                "max_marks": 10.0,
                "pass_percentage": 40.0,
                "instructions": "Select the single best answer for each question. Instant scoring is automated.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "mcq",
                        "question_text": "The maximum rectification efficiency of a half-wave rectifier is:",
                        "option_a": "40.6%",
                        "option_b": "50.0%",
                        "option_c": "81.2%",
                        "option_d": "90.4%",
                        "correct_option": "A",
                        "max_marks": 2.5,
                        "model_answer": "Option A is correct. The theoretical maximum efficiency of a half-wave rectifier is 40.6%."
                    },
                    {
                        "question_number": "2",
                        "question_type": "mcq",
                        "question_text": "The ripple factor of a full-wave bridge rectifier is:",
                        "option_a": "1.21",
                        "option_b": "0.482",
                        "option_c": "0.707",
                        "option_d": "0.500",
                        "correct_option": "B",
                        "max_marks": 2.5,
                        "model_answer": "Option B is correct. Ripple factor for full-wave rectifier without filter is sqrt((Irms/Idc)^2 - 1) = 0.482."
                    },
                    {
                        "question_number": "3",
                        "question_type": "mcq",
                        "question_text": "In a Zener diode operating in breakdown region, the voltage across it remains:",
                        "option_a": "Zero",
                        "option_b": "Proportional to current",
                        "option_c": "Virtually constant",
                        "option_d": "Oscillating",
                        "correct_option": "C",
                        "max_marks": 2.5,
                        "model_answer": "Option C is correct. Zener breakdown maintains an almost constant voltage across terminal irrespective of current."
                    },
                    {
                        "question_number": "4",
                        "question_type": "mcq",
                        "question_text": "Which transistor configuration provides the highest voltage gain?",
                        "option_a": "Common Base (CB)",
                        "option_b": "Common Collector (CC)",
                        "option_c": "Common Emitter (CE)",
                        "option_d": "All have identical gain",
                        "correct_option": "C",
                        "max_marks": 2.5,
                        "model_answer": "Option C is correct. The CE configuration provides high voltage and current gain, giving maximum power gain."
                    }
                ]
            },
            {
                "title": "Unit 3: Small Signal Audio Amplifiers Slip Test",
                "type": "slip_test",
                "max_marks": 15.0,
                "pass_percentage": 40.0,
                "instructions": "Answer questions on RC-coupled audio frequency amplifiers.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "Explain the role of emitter bypass capacitor CE in a Common Emitter amplifier. What happens if CE is removed?",
                        "max_marks": 7.5,
                        "model_answer": "CE provides a low impedance path to AC ground, preventing AC degenerative negative feedback across RE and preserving maximum voltage gain. If removed, RE causes negative feedback reducing gain but improving stability and bandwidth.",
                        "criteria": [
                            {"criterion_name": "AC Ground Bypass Role", "max_marks": 4.0, "guidance": "Mentions low capacitive reactance Xc << RE at signal frequencies."},
                            {"criterion_name": "Removal Effect Analysis", "max_marks": 3.5, "guidance": "Explains negative feedback, reduction in gain, and bandwidth expansion."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_type": "subjective",
                        "question_text": "Sketch the frequency response curve of a two-stage RC-coupled amplifier. Mark the lower (fL) and upper (fH) cutoff frequencies and explain causes of drop in gain.",
                        "max_marks": 7.5,
                        "model_answer": "Graph of Gain vs Frequency shows flat mid-frequency region. Gain drops at low frequencies due to coupling and bypass capacitors; drops at high frequencies due to junction capacitances and stray wiring capacitance.",
                        "criteria": [
                            {"criterion_name": "Frequency Response Plot", "max_marks": 4.0, "guidance": "Neat log frequency vs gain curve with 3dB cutoff points marked."},
                            {"criterion_name": "Attenuation Reasons", "max_marks": 3.5, "guidance": "Identifies coupling capacitor effect at low end and parasitic capacitance at high end."}
                        ]
                    }
                ]
            }
        ]
    },
    {
        "lecturer": {
            "full_name": "Prof. Priya Kulkarni",
            "username": "prof_priya",
            "email": "priya.kulkarni@college.edu",
            "password": "Priya@123",
            "subject": "Data Structures & Algorithms",
            "mobile": "9849033445",
            "specialization": "Algorithms & Computational Complexity"
        },
        "department": "CSE",
        "semester": "Semester 3",
        "section": "A",
        "students": [
            {"name": "VEMULA RAHUL", "pin": "26054-CSE-011", "phone": "9440112233"},
            {"name": "KOPPULA ANANYA", "pin": "26054-CSE-012", "phone": "9440223344"},
            {"name": "GANGULA TEJA", "pin": "26054-CSE-013", "phone": "9440334455"},
            {"name": "POTHULA SNEHA", "pin": "26054-CSE-014", "phone": "9440445566"},
            {"name": "MOHAMMED AFROZ", "pin": "26054-CSE-015", "phone": "9440556677"}
        ],
        "assessments": [
            {
                "title": "Unit 1: Arrays, Stacks & Complexity MCQ",
                "type": "mcq_test",
                "max_marks": 10.0,
                "pass_percentage": 40.0,
                "instructions": "Attempt all multiple choice questions on linear data structures.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "mcq",
                        "question_text": "What is the worst-case time complexity of searching an element in an unsorted array of size N?",
                        "option_a": "O(1)",
                        "option_b": "O(log N)",
                        "option_c": "O(N)",
                        "option_d": "O(N^2)",
                        "correct_option": "C",
                        "max_marks": 2.5,
                        "model_answer": "Option C is correct. Linear search visits all N elements in the worst case."
                    },
                    {
                        "question_number": "2",
                        "question_type": "mcq",
                        "question_text": "Which data structure operates on the Last-In First-Out (LIFO) principle?",
                        "option_a": "Queue",
                        "option_b": "Stack",
                        "option_c": "Binary Tree",
                        "option_d": "Linked List",
                        "correct_option": "B",
                        "max_marks": 2.5,
                        "model_answer": "Option B is correct. A stack always pops the most recently pushed item first."
                    },
                    {
                        "question_number": "3",
                        "question_type": "mcq",
                        "question_text": "The prefix form of the infix expression (A + B) * C is:",
                        "option_a": "* + A B C",
                        "option_b": "+ * A B C",
                        "option_c": "A B + C *",
                        "option_d": "* A + B C",
                        "correct_option": "A",
                        "max_marks": 2.5,
                        "model_answer": "Option A is correct. (A+B)*C becomes *(+AB)C = * + A B C."
                    },
                    {
                        "question_number": "4",
                        "question_type": "mcq",
                        "question_text": "Time complexity to insert a node at the head of a singly linked list is:",
                        "option_a": "O(1)",
                        "option_b": "O(N)",
                        "option_c": "O(log N)",
                        "option_d": "O(N log N)",
                        "correct_option": "A",
                        "max_marks": 2.5,
                        "model_answer": "Option A is correct. Inserting at the head requires updating pointer references in constant time."
                    }
                ]
            },
            {
                "title": "Unit 2: Stack & Queue Applications Slip Test",
                "type": "slip_test",
                "max_marks": 20.0,
                "pass_percentage": 40.0,
                "instructions": "Demonstrate step-by-step manual conversions and algorithm walkthroughs.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "Convert the infix expression: A + B * (C - D) / E into postfix notation showing the status of the operator stack at each character scan.",
                        "max_marks": 10.0,
                        "model_answer": "Scanned tokens produce postfix output: A B C D - * E / +. Stack transitions respect operator precedence: parentheses highest, then *, / left-to-right, then +.",
                        "criteria": [
                            {"criterion_name": "Stack State Tracking", "max_marks": 5.0, "guidance": "Table showing Symbol Scanned, Operator Stack, Postfix Output for all tokens."},
                            {"criterion_name": "Final Postfix Expression", "max_marks": 5.0, "guidance": "Final answer A B C D - * E / + correctly derived."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_type": "subjective",
                        "question_text": "Explain circular queues. Write C functions or detailed pseudo-code for enqueue() and dequeue() operations with overflow and underflow conditions.",
                        "max_marks": 10.0,
                        "model_answer": "Circular queue connects rear to front circularly using modulo arithmetic ((rear + 1) % MAX) to eliminate memory wastage in linear queues. Full when (rear + 1) % MAX == front. Empty when front == -1.",
                        "criteria": [
                            {"criterion_name": "Concept & Modulo Addressing", "max_marks": 4.0, "guidance": "Clear explanation of linear queue memory flaw and circular modulo mechanism."},
                            {"criterion_name": "Enqueue & Dequeue Algorithms", "max_marks": 6.0, "guidance": "Syntactically sound logic with boundary checks for full and empty states."}
                        ]
                    }
                ]
            },
            {
                "title": "Unit 3: Binary Search Trees & Traversal Slip Test",
                "type": "slip_test",
                "max_marks": 15.0,
                "pass_percentage": 40.0,
                "instructions": "Draw BST structure and write recursive tree traversals.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "Construct a Binary Search Tree (BST) by inserting numbers in this sequence: 45, 23, 67, 12, 34, 56, 89, 29. Show the resulting tree and its Inorder traversal.",
                        "max_marks": 8.0,
                        "model_answer": "Root is 45; left subtree contains 23 (with left child 12, right child 34 containing left child 29); right subtree contains 67 (left child 56, right child 89). Inorder traversal yields sorted order: 12, 23, 29, 34, 45, 56, 67, 89.",
                        "criteria": [
                            {"criterion_name": "BST Structure Diagram", "max_marks": 5.0, "guidance": "Correct binary search tree with left < root < right property at every node."},
                            {"criterion_name": "Inorder Traversal", "max_marks": 3.0, "guidance": "Correct monotonically increasing sorted sequence."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_type": "subjective",
                        "question_text": "Compare Breadth First Search (BFS) and Depth First Search (DFS) for graph traversal in terms of data structures used and time complexity.",
                        "max_marks": 7.0,
                        "model_answer": "BFS uses Queue (FIFO) exploring level by level; DFS uses Stack / Recursion exploring branch by branch. Both have time complexity O(V + E) for adjacency list representations.",
                        "criteria": [
                            {"criterion_name": "Data Structure Distinction", "max_marks": 4.0, "guidance": "Explicitly identifies Queue for BFS vs Stack/Call-stack for DFS."},
                            {"criterion_name": "Complexity & Applications", "max_marks": 3.0, "guidance": "States O(V+E) time complexity and shortest path application for unweighted graphs."}
                        ]
                    }
                ]
            }
        ]
    },
    {
        "lecturer": {
            "full_name": "Dr. Vikram Mehta",
            "username": "dr_vikram",
            "email": "vikram.mehta@college.edu",
            "password": "Vikram@123",
            "subject": "Computer Networks & Cloud Security",
            "mobile": "9849055667",
            "specialization": "Network Protocols & Cyber Defense"
        },
        "department": "IT",
        "semester": "Semester 4",
        "section": "A",
        "students": [
            {"name": "SINGH ARJUN", "pin": "26054-IT-021", "phone": "9871011223"},
            {"name": "DESHMUKH KAVYA", "pin": "26054-IT-022", "phone": "9871022334"},
            {"name": "JADHAV KARTHIK", "pin": "26054-IT-023", "phone": "9871033445"},
            {"name": "PATEL RIDDHI", "pin": "26054-IT-024", "phone": "9871044556"},
            {"name": "SYED MANSOOR", "pin": "26054-IT-025", "phone": "9871055667"}
        ],
        "assessments": [
            {
                "title": "Unit 1: OSI Model & Network Architectures MCQ",
                "type": "mcq_test",
                "max_marks": 10.0,
                "pass_percentage": 40.0,
                "instructions": "Answer questions on OSI layers, protocol data units, and network standards.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "mcq",
                        "question_text": "Which OSI layer is responsible for end-to-end process-to-process communication and flow control?",
                        "option_a": "Network Layer",
                        "option_b": "Transport Layer",
                        "option_c": "Data Link Layer",
                        "option_d": "Session Layer",
                        "correct_option": "B",
                        "max_marks": 2.5,
                        "model_answer": "Option B is correct. Transport layer (TCP/UDP) handles process-to-process communication using port numbers."
                    },
                    {
                        "question_number": "2",
                        "question_type": "mcq",
                        "question_text": "What is the size of an IPv4 address in bits?",
                        "option_a": "16 bits",
                        "option_b": "32 bits",
                        "option_c": "64 bits",
                        "option_d": "128 bits",
                        "correct_option": "B",
                        "max_marks": 2.5,
                        "model_answer": "Option B is correct. IPv4 uses 32-bit addresses formatted as 4 octets."
                    },
                    {
                        "question_number": "3",
                        "question_type": "mcq",
                        "question_text": "Which protocol resolves an IP address to a physical MAC address on a local network?",
                        "option_a": "DNS",
                        "option_b": "DHCP",
                        "option_c": "ARP",
                        "option_d": "RARP",
                        "correct_option": "C",
                        "max_marks": 2.5,
                        "model_answer": "Option C is correct. Address Resolution Protocol (ARP) translates IP addresses to MAC addresses."
                    },
                    {
                        "question_number": "4",
                        "question_type": "mcq",
                        "question_text": "The default TCP port for Secure HTTP (HTTPS) is:",
                        "option_a": "80",
                        "option_b": "22",
                        "option_c": "8080",
                        "option_d": "443",
                        "correct_option": "D",
                        "max_marks": 2.5,
                        "model_answer": "Option D is correct. Port 443 is the standard port for TLS/HTTPS traffic."
                    }
                ]
            },
            {
                "title": "Unit 2: IP Subnetting & Addressing Slip Test",
                "type": "slip_test",
                "max_marks": 20.0,
                "pass_percentage": 40.0,
                "instructions": "Show complete binary and decimal subnet calculations.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "A company is assigned the Class C network 192.168.10.0/24. They need to divide it into 4 equal subnets. Calculate: (a) Subnet mask (b) Number of usable hosts per subnet (c) Network and broadcast addresses of Subnet 1 and Subnet 2.",
                        "max_marks": 10.0,
                        "model_answer": "To get 4 subnets, borrow 2 bits (/26). (a) Mask: 255.255.255.192. (b) Usable hosts: 2^6 - 2 = 62. (c) Subnet 1: Net 192.168.10.0, BC 192.168.10.63, range .1-.62. Subnet 2: Net 192.168.10.64, BC 192.168.10.127, range .65-.126.",
                        "criteria": [
                            {"criterion_name": "Subnet Mask Derivation", "max_marks": 3.0, "guidance": "Identifies /26 and gives 255.255.255.192."},
                            {"criterion_name": "Host Count Formula", "max_marks": 3.0, "guidance": "Applies 2^(32-26) - 2 = 62 usable host addresses."},
                            {"criterion_name": "Subnet Ranges", "max_marks": 4.0, "guidance": "Accurate network, broadcast, and valid host bounds for subnets 1 and 2."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_type": "subjective",
                        "question_text": "Explain the TCP Three-Way Handshake mechanism for connection establishment and Four-Way Handshake for termination with sequence diagram.",
                        "max_marks": 10.0,
                        "model_answer": "Establishment: Client sends SYN(seq=x) -> Server replies SYN-ACK(seq=y, ack=x+1) -> Client sends ACK(ack=y+1). Termination: Client sends FIN -> Server sends ACK -> Server sends FIN -> Client sends ACK and enters TIME_WAIT.",
                        "criteria": [
                            {"criterion_name": "Connection Sequence (SYN/ACK)", "max_marks": 5.0, "guidance": "Accurate three-way handshake diagram with flags and sequence/acknowledgment numbers."},
                            {"criterion_name": "Termination Sequence (FIN/ACK)", "max_marks": 5.0, "guidance": "Clear four-step disconnect flow and explanation of graceful close."}
                        ]
                    }
                ]
            },
            {
                "title": "Unit 3: Firewalls & Cryptography Slip Test",
                "type": "slip_test",
                "max_marks": 15.0,
                "pass_percentage": 40.0,
                "instructions": "Answer questions on symmetric vs asymmetric encryption and firewall filtering.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "Differentiate between Symmetric Key Cryptography (e.g., AES) and Asymmetric Key Cryptography (e.g., RSA). Explain how digital signatures provide authenticity and non-repudiation.",
                        "max_marks": 8.0,
                        "model_answer": "Symmetric uses single shared key for encryption and decryption (high speed); asymmetric uses public/private key pair (solves key distribution). Digital signatures encrypt message hash with private key; verified with sender's public key.",
                        "criteria": [
                            {"criterion_name": "Symmetric vs Asymmetric Comparison", "max_marks": 4.0, "guidance": "Contrasts key count, performance speed, and distribution trade-offs."},
                            {"criterion_name": "Digital Signature Mechanism", "max_marks": 4.0, "guidance": "Hash creation, private key signing, and public key verification explained."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_type": "subjective",
                        "question_text": "Explain the working of a Stateful Packet Inspection (SPI) firewall compared to a stateless packet filter.",
                        "max_marks": 7.0,
                        "model_answer": "Stateless filters inspect each packet in isolation against static rules (IP, port). Stateful firewalls track connection state in a dynamic state table, allowing return traffic for established sessions.",
                        "criteria": [
                            {"criterion_name": "Inspection Comparison", "max_marks": 4.0, "guidance": "Contrasts stateless header matching with dynamic state-aware tracking."},
                            {"criterion_name": "State Table Mechanics", "max_marks": 3.0, "guidance": "Mentions tracking SYN, ESTABLISHED, and FIN packet states."}
                        ]
                    }
                ]
            }
        ]
    },
    {
        "lecturer": {
            "full_name": "Dr. Ananya Sen",
            "username": "dr_ananya",
            "email": "ananya.sen@college.edu",
            "password": "Ananya@123",
            "subject": "Microcontrollers & Embedded IoT",
            "mobile": "9849077889",
            "specialization": "Embedded Systems & Sensor Networks"
        },
        "department": "EEE",
        "semester": "Semester 5",
        "section": "A",
        "students": [
            {"name": "DASARI VARUN", "pin": "26054-EEE-031", "phone": "9701112233"},
            {"name": "GOUD MEGHANA", "pin": "26054-EEE-032", "phone": "9701223344"},
            {"name": "BANOTH VISHAL", "pin": "26054-EEE-033", "phone": "9701334455"},
            {"name": "THOTA DEEPIKA", "pin": "26054-EEE-034", "phone": "9701445566"},
            {"name": "CHEVVURI NIKHIL", "pin": "26054-EEE-035", "phone": "9701556677"}
        ],
        "assessments": [
            {
                "title": "Unit 1: 8051 & ARM Cortex Architecture MCQ",
                "type": "mcq_test",
                "max_marks": 10.0,
                "pass_percentage": 40.0,
                "instructions": "Select the correct option for microcontroller architectures and register sets.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "mcq",
                        "question_text": "The standard 8051 microcontroller has how many 8-bit bidirectional I/O ports?",
                        "option_a": "2",
                        "option_b": "4",
                        "option_c": "6",
                        "option_d": "8",
                        "correct_option": "B",
                        "max_marks": 2.5,
                        "model_answer": "Option B is correct. 8051 has 4 bidirectional 8-bit ports (P0, P1, P2, P3), totaling 32 I/O pins."
                    },
                    {
                        "question_number": "2",
                        "question_type": "mcq",
                        "question_text": "Which serial communication protocol uses two wires: SDA and SCL?",
                        "option_a": "SPI",
                        "option_b": "UART",
                        "option_c": "I2C",
                        "option_d": "CAN",
                        "correct_option": "C",
                        "max_marks": 2.5,
                        "model_answer": "Option C is correct. Inter-Integrated Circuit (I2C) uses Serial Data (SDA) and Serial Clock (SCL)."
                    },
                    {
                        "question_number": "3",
                        "question_type": "mcq",
                        "question_text": "The on-chip RAM size of the standard 8051 microcontroller is:",
                        "option_a": "64 bytes",
                        "option_b": "128 bytes",
                        "option_c": "256 bytes",
                        "option_d": "512 bytes",
                        "correct_option": "B",
                        "max_marks": 2.5,
                        "model_answer": "Option B is correct. Classic 8051 contains 128 bytes of internal data RAM."
                    },
                    {
                        "question_number": "4",
                        "question_type": "mcq",
                        "question_text": "In embedded systems, what does PWM stand for?",
                        "option_a": "Pulse Wave Modulation",
                        "option_b": "Power Width Measurement",
                        "option_c": "Pulse Width Modulation",
                        "option_d": "Phase Width Multiplexing",
                        "correct_option": "C",
                        "max_marks": 2.5,
                        "model_answer": "Option C is correct. Pulse Width Modulation (PWM) controls power delivery by varying duty cycle."
                    }
                ]
            },
            {
                "title": "Unit 2: Timers, Interrupts & ADC Interfacing Slip Test",
                "type": "slip_test",
                "max_marks": 20.0,
                "pass_percentage": 40.0,
                "instructions": "Solve calculation problems on timer delays and sensor ADC resolution.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "An 8051 microcontroller operates at crystal frequency 11.0592 MHz. Calculate the initial hex values to load into TH1 and TL1 for Timer 1 in Mode 1 (16-bit) to generate a delay of 5 milliseconds.",
                        "max_marks": 10.0,
                        "model_answer": "Machine cycle frequency = 11.0592 MHz / 12 = 921.6 kHz. Machine cycle period = 1.085 us. Required counts = 5000 us / 1.085069 us = 4608 counts. Initial load = 65536 - 4608 = 60928 = 0xEE00. Therefore, TH1 = 0xEE and TL1 = 0x00.",
                        "criteria": [
                            {"criterion_name": "Machine Cycle Frequency", "max_marks": 3.0, "guidance": "Divides crystal frequency by 12 to find 921.6 kHz (1.085 us)."},
                            {"criterion_name": "Count Calculation", "max_marks": 4.0, "guidance": "5ms / 1.085us gives 4608 timer ticks."},
                            {"criterion_name": "Register Value (Hex)", "max_marks": 3.0, "guidance": "65536 - 4608 = 0xEE00, setting TH1=0xEE and TL1=0x00."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_type": "subjective",
                        "question_text": "Explain the architecture of MQTT protocol for IoT. Describe the roles of Broker, Publisher, and Subscriber, and compare QoS levels 0, 1, and 2.",
                        "max_marks": 10.0,
                        "model_answer": "MQTT is a lightweight publish-subscribe messaging protocol over TCP. Publisher sends sensor data to topic on Broker; Broker filters and routes to Subscribers. QoS 0 is at most once (fire and forget); QoS 1 is at least once (acknowledged); QoS 2 is exactly once (four-step handshake).",
                        "criteria": [
                            {"criterion_name": "Pub/Sub Architecture & Broker", "max_marks": 5.0, "guidance": "Clear explanation of client/broker interaction and topic hierarchy."},
                            {"criterion_name": "Quality of Service (QoS 0, 1, 2)", "max_marks": 5.0, "guidance": "Accurate comparison of delivery guarantees and network overhead."}
                        ]
                    }
                ]
            },
            {
                "title": "Unit 3: Sensor Interfacing & Actuators Slip Test",
                "type": "slip_test",
                "max_marks": 15.0,
                "pass_percentage": 40.0,
                "instructions": "Explain circuit connections for relay driving and stepper motor control.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "Draw an interfacing diagram showing how an 8051 or Arduino pin controls an AC lamp using a 5V electromagnetic relay. Explain why a freewheeling diode (1N4007) and transistor driver (BC547) are required.",
                        "max_marks": 8.0,
                        "model_answer": "Microcontroller pin cannot source sufficient current (~70mA) to energize relay coil, so NPN transistor (BC547) acts as current amplifier/switch. Freewheeling diode connected in reverse-parallel across coil protects transistor from back-EMF inductive voltage spikes when coil de-energizes.",
                        "criteria": [
                            {"criterion_name": "Interfacing Schematic", "max_marks": 4.0, "guidance": "Complete diagram showing MCU pin, base resistor, transistor, relay coil, diode, and AC load."},
                            {"criterion_name": "Flyback Diode & Transistor Role", "max_marks": 4.0, "guidance": "Clearly explains inductive back-EMF suppression and current amplification."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_type": "subjective",
                        "question_text": "Explain the difference between SPI and I2C protocols in terms of bus lines, master-slave addressing, data rate, and hardware complexity.",
                        "max_marks": 7.0,
                        "model_answer": "SPI uses 4 lines (MOSI, MISO, SCK, CS) with dedicated chip-select lines per slave, achieves higher speeds (>10 Mbps), full-duplex. I2C uses 2 lines (SDA, SCL) with 7-bit software addresses, pull-up resistors, lower speeds (100k-3.4M), half-duplex.",
                        "criteria": [
                            {"criterion_name": "Bus Topology Comparison", "max_marks": 4.0, "guidance": "Identifies 4-wire SPI vs 2-wire I2C with pin names."},
                            {"criterion_name": "Speed, Addressing & Complexity", "max_marks": 3.0, "guidance": "Contrasts hardware chip-select with 7-bit software addressing and speeds."}
                        ]
                    }
                ]
            }
        ]
    },
    {
        "lecturer": {
            "full_name": "Prof. Rajesh Nair",
            "username": "prof_rajesh",
            "email": "rajesh.nair@college.edu",
            "password": "Rajesh@123",
            "subject": "Applied Thermodynamics & Heat Transfer",
            "mobile": "9849099001",
            "specialization": "Thermal Engineering & Energy Systems"
        },
        "department": "MECH",
        "semester": "Semester 4",
        "section": "A",
        "students": [
            {"name": "SHAIK BILAL", "pin": "26054-MECH-041", "phone": "9618011223"},
            {"name": "KONDAPALLI HARISH", "pin": "26054-MECH-042", "phone": "9618022334"},
            {"name": "NANDIGAMA POOJA", "pin": "26054-MECH-043", "phone": "9618033445"},
            {"name": "POLA ADITYA", "pin": "26054-MECH-044", "phone": "9618044556"},
            {"name": "MERUGU SRAVANI", "pin": "26054-MECH-045", "phone": "9618055667"}
        ],
        "assessments": [
            {
                "title": "Unit 1: Laws of Thermodynamics & Carnot Cycle MCQ",
                "type": "mcq_test",
                "max_marks": 10.0,
                "pass_percentage": 40.0,
                "instructions": "Select the correct option for thermodynamic laws and cycle properties.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "mcq",
                        "question_text": "The First Law of Thermodynamics is a statement of:",
                        "option_a": "Conservation of momentum",
                        "option_b": "Conservation of energy",
                        "option_c": "Conservation of mass",
                        "option_d": "Increase in entropy",
                        "correct_option": "B",
                        "max_marks": 2.5,
                        "model_answer": "Option B is correct. First law states that energy can neither be created nor destroyed: dQ = dU + dW."
                    },
                    {
                        "question_number": "2",
                        "question_type": "mcq",
                        "question_text": "A Carnot engine operates between temperatures 600 K and 300 K. Its thermal efficiency is:",
                        "option_a": "25%",
                        "option_b": "40%",
                        "option_c": "50%",
                        "option_d": "75%",
                        "correct_option": "C",
                        "max_marks": 2.5,
                        "model_answer": "Option C is correct. Carnot efficiency = 1 - (T_cold / T_hot) = 1 - (300 / 600) = 0.50 (50%)."
                    },
                    {
                        "question_number": "3",
                        "question_type": "mcq",
                        "question_text": "Which property remains constant during an isentropic process?",
                        "option_a": "Pressure",
                        "option_b": "Volume",
                        "option_c": "Temperature",
                        "option_d": "Entropy",
                        "correct_option": "D",
                        "max_marks": 2.5,
                        "model_answer": "Option D is correct. An isentropic process is reversible and adiabatic, so entropy remains constant (dS = 0)."
                    },
                    {
                        "question_number": "4",
                        "question_type": "mcq",
                        "question_text": "The air standard Otto cycle consists of:",
                        "option_a": "Two constant pressure and two isentropic processes",
                        "option_b": "Two constant volume and two isentropic processes",
                        "option_c": "Two isothermal and two isentropic processes",
                        "option_d": "Two constant volume and two constant pressure processes",
                        "correct_option": "B",
                        "max_marks": 2.5,
                        "model_answer": "Option B is correct. Otto cycle comprises two reversible adiabatic (isentropic) and two isochoric (constant volume) processes."
                    }
                ]
            },
            {
                "title": "Unit 2: Air Standard Cycles & Efficiency Slip Test",
                "type": "slip_test",
                "max_marks": 20.0,
                "pass_percentage": 40.0,
                "instructions": "Derive efficiency equations and solve thermodynamic numericals.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "Derive the air standard efficiency of an Otto cycle in terms of compression ratio (r) and ratio of specific heats (gamma). If an engine has compression ratio r = 8.5 and gamma = 1.4, calculate its thermal efficiency.",
                        "max_marks": 10.0,
                        "model_answer": "eta_otto = 1 - 1 / (r^(gamma - 1)). For r = 8.5 and gamma = 1.4: eta = 1 - 1 / (8.5^0.4) = 1 - 1 / 2.3535 = 1 - 0.4249 = 0.5751 (57.51%).",
                        "criteria": [
                            {"criterion_name": "P-V and T-S Cycle Diagrams", "max_marks": 3.0, "guidance": "Neat P-V and T-S diagrams with labeled process numbers 1-2, 2-3, 3-4, 4-1."},
                            {"criterion_name": "Algebraic Derivation", "max_marks": 4.0, "guidance": "Heat supplied Q_in = m*Cv*(T3-T2), Q_out = m*Cv*(T4-T1), leading to 1 - 1/(r^(gamma-1))."},
                            {"criterion_name": "Numerical Evaluation", "max_marks": 3.0, "guidance": "Accurate substitution giving 57.51% efficiency."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_text": "Explain Fourier's law of heat conduction. A plane brick wall of thickness 0.25 m and thermal conductivity k = 0.7 W/m.K has surface temperatures 120 deg C inside and 30 deg C outside. Calculate the rate of heat loss per square meter of wall area.",
                        "max_marks": 10.0,
                        "model_answer": "Fourier's law states q = -k * (dT/dx) = k * (T1 - T2) / L. Rate of heat loss q/A = 0.7 * (120 - 30) / 0.25 = 0.7 * 90 / 0.25 = 63 / 0.25 = 252 W/m^2.",
                        "criteria": [
                            {"criterion_name": "Fourier Law Statement & Formula", "max_marks": 4.0, "guidance": "States proportionality to temperature gradient and normal surface area with minus sign explanation."},
                            {"criterion_name": "Heat Flux Calculation", "max_marks": 6.0, "guidance": "Correct substitution q/A = 252 W/m^2 with appropriate units."}
                        ]
                    }
                ]
            },
            {
                "title": "Unit 3: Heat Exchangers & Radiation Slip Test",
                "type": "slip_test",
                "max_marks": 15.0,
                "pass_percentage": 40.0,
                "instructions": "Answer questions on Log Mean Temperature Difference (LMTD) and Stefan-Boltzmann radiation.",
                "questions": [
                    {
                        "question_number": "1",
                        "question_type": "subjective",
                        "question_text": "Define Logarithmic Mean Temperature Difference (LMTD). Why is LMTD higher for counter-flow heat exchangers compared to parallel-flow heat exchangers for identical temperature endpoints?",
                        "max_marks": 7.5,
                        "model_answer": "LMTD = (theta1 - theta2) / ln(theta1 / theta2). In counter-flow, temperature difference between hot and cold fluid remains more uniform along length, producing a larger effective mean temperature difference and requiring less heat transfer area.",
                        "criteria": [
                            {"criterion_name": "LMTD Formula & Definition", "max_marks": 3.5, "guidance": "Correct formula with terminal temperature differences theta1 and theta2 defined."},
                            {"criterion_name": "Counter vs Parallel Analysis", "max_marks": 4.0, "guidance": "Explains uniform delta-T profile and reduced surface area requirement."}
                        ]
                    },
                    {
                        "question_number": "2",
                        "question_type": "subjective",
                        "question_text": "State Stefan-Boltzmann law and Wien's displacement law of thermal radiation. Calculate total emissive power of a black body at temperature 1000 K (sigma = 5.67 x 10^-8 W/m^2.K^4).",
                        "max_marks": 7.5,
                        "model_answer": "Stefan-Boltzmann law: Eb = sigma * T^4. For T = 1000 K, Eb = 5.67 * 10^-8 * (1000)^4 = 5.67 * 10^-8 * 10^12 = 56,700 W/m^2 (56.7 kW/m^2). Wien's law: lambda_max * T = constant = 2898 um.K.",
                        "criteria": [
                            {"criterion_name": "Laws Statement", "max_marks": 3.5, "guidance": "Statements for Eb = sigma*T^4 and lambda_max*T = b."},
                            {"criterion_name": "Blackbody Emissive Power Calculation", "max_marks": 4.0, "guidance": "Accurate calculation giving 56,700 W/m^2."}
                        ]
                    }
                ]
            }
        ]
    }
]

def seed_sample_ecosystem(app_instance=None):
    global app
    print("[*] Starting multi-tenant academic ecosystem seeding...")
    created_summary = []

    target_app = app_instance or app
    if target_app is None:
        from app import create_app
        target_app = create_app()

    with target_app.app_context():
        for item in SEED_DATA:
            lec_conf = item["lecturer"]
            # 1. Check or register lecturer
            existing = next((l for l in LecturerService._load_lecturers() if l.get("username") == lec_conf["username"] or l.get("email") == lec_conf["email"]), None)
            if existing:
                lec_id = existing["id"]
                LecturerService.approve_lecturer(lec_id)
                print(f"[+] Lecturer {lec_conf['full_name']} already exists ({lec_id}) - approved.")
            else:
                ok, l_data, msg = LecturerService.register_lecturer(
                    full_name=lec_conf["full_name"],
                    username=lec_conf["username"],
                    email=lec_conf["email"],
                    password=lec_conf["password"],
                    subject=lec_conf["subject"],
                    mobile=lec_conf["mobile"],
                    specialization=lec_conf["specialization"]
                )
                if not ok or not l_data:
                    print(f"[-] Failed to register lecturer {lec_conf['full_name']}: {msg}")
                    continue
                lec_id = l_data["id"]
                LecturerService.approve_lecturer(lec_id)
                print(f"[+] Created and Approved Lecturer: {lec_conf['full_name']} (ID: {lec_id})")

            # 2. Create Assessments
            created_asms = []
            for asm_conf in item["assessments"]:
                existing_asms = AssessmentService.get_all_assessments(teacher_id=lec_id)
                found_asm = next((a for a in existing_asms if a.get("title") == asm_conf["title"]), None)
                if found_asm:
                    asm_id = found_asm["id"]
                    if not found_asm.get("questions") and asm_conf.get("questions"):
                        formatted_q = []
                        for idx, q in enumerate(asm_conf["questions"], start=1):
                            q_copy = dict(q)
                            if "id" not in q_copy or not q_copy["id"]:
                                q_copy["id"] = str(uuid.uuid4())
                            if "question_number" not in q_copy or not q_copy["question_number"]:
                                q_copy["question_number"] = str(idx)
                            formatted_q.append(q_copy)

                        def _attach_questions(a, tenant_asms, tid, q_data=formatted_q):
                            a["questions"] = q_data
                        AssessmentService._find_and_update_tenant_assessment(asm_id, _attach_questions)
                    AssessmentService.toggle_publish(asm_id, publish=True)
                    created_asms.append({"id": asm_id, "title": found_asm["title"], "type": found_asm["assessment_type"]})
                    print(f"    [~] Assessment '{asm_conf['title']}' exists ({asm_id}) - published.")
                else:
                    ok, asm_id, msg = AssessmentService.create_assessment(
                        title=asm_conf["title"],
                        assessment_type=asm_conf["type"],
                        max_marks=asm_conf["max_marks"],
                        assessment_date=str(date.today()),
                        instructions=asm_conf["instructions"],
                        pass_percentage=asm_conf["pass_percentage"],
                        questions=asm_conf["questions"],
                        created_by_id=lec_id,
                        unit_topic=asm_conf["title"].split(":")[0] if ":" in asm_conf["title"] else "Unit 1",
                        subject_code=lec_conf["subject"]
                    )
                    if ok:
                        AssessmentService.toggle_publish(asm_id, publish=True)
                        created_asms.append({"id": asm_id, "title": asm_conf["title"], "type": asm_conf["type"]})
                        print(f"    [+] Created & Published Assessment: {asm_conf['title']} ({asm_id})")

            # 3. Register & Approve Students
            created_students = []
            for s in item["students"]:
                # Register student
                StudentService.register_student(
                    full_name=s["name"],
                    pin=s["pin"],
                    lecturer_id=lec_id,
                    branch=item["department"],
                    semester=item["semester"],
                    section=item["section"],
                    contact_phone=s["phone"]
                )
                # Approve
                pending = StudentService.get_pending_students_for_lecturer(lec_id)
                match_reg = next((p for p in pending if p["pin"] == s["pin"]), None)
                if match_reg:
                    StudentService.approve_student_registration(match_reg["id"], lec_id)
                    created_students.append({"name": s["name"], "pin": s["pin"]})
                    print(f"    [+] Enrolled & Approved Student: {s['name']} (PIN: {s['pin']})")
                else:
                    created_students.append({"name": s["name"], "pin": s["pin"]})

            # 4. Create sample live submissions for testing
            if created_asms and created_students:
                first_mcq_asm = next((a for a in created_asms if a["type"] == "mcq_test"), None)
                if first_mcq_asm:
                    # Submit 2 student test attempts so teacher dashboard has live data
                    for stud_idx in range(min(2, len(created_students))):
                        stud = created_students[stud_idx]
                        reg = StudentService.get_registration_by_pin(stud["pin"])
                        if reg:
                            draft = SubmissionService.get_or_create_draft_submission(first_mcq_asm["id"], reg["id"])
                            # Answer MCQ choices: pick correct options
                            ans_map = {}
                            full_asm = AssessmentService.get_assessment_by_id(first_mcq_asm["id"])
                            if full_asm and full_asm.get("questions"):
                                for q in full_asm["questions"]:
                                    qid = q.get("id") or str(uuid.uuid4())
                                    ans_map[qid] = q.get("correct_option", "A")
                            SubmissionService.finalize_submission(
                                submission_id=draft["id"],
                                client_ip="127.0.0.1",
                                mcq_answers=ans_map
                            )
                            print(f"    [OK] Simulated completed submission for student {stud['name']} on '{first_mcq_asm['title']}'")

            created_summary.append({
                "lecturer": lec_conf,
                "department": item["department"],
                "semester": item["semester"],
                "students": created_students,
                "assessments": created_asms
            })

    print("[*] Academic sample ecosystem seeding completed successfully!")
    return created_summary

if __name__ == "__main__":
    seed_sample_ecosystem()

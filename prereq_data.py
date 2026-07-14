"""
UTP Course Prerequisites - defines which courses unlock which.
Format: {course_code: [list of prerequisite course codes]}
"""

PREREQUISITES = {
    # Computer Science
    "UCB1033": ["UCB1013"],  # OOP requires Structured Programming
    "UCB2033": ["UCB1033"],  # Algorithm & Data Structure requires OOP
    "UCB2023": ["UCB1043"],  # Data & Info Management requires Discrete Math
    "UCB2043": ["UCB2033"],  # Software Eng & HCI requires Algo & DS
    "UCB2053": ["UCB2033", "UCB2013"],  # AI requires Algo & DS + Stats
    "UCB3013": ["UCB2013", "UCB2023"],  # Data Science requires Stats + Data Management
    "UCB3023": ["UCB1023"],  # Embedded Systems requires Computer Systems
    "UCB3043": ["UCB1053"],  # Computer Security requires Data Comm & Network
    "UCB3053": ["UCB2013"],  # Modelling & Simulation requires Stats
    "UCB4053": ["UCB2033"],  # Distributed Computing requires Algo & DS
    "UCB4012": ["UCB2043"],  # FYP I requires Software Eng
    "UCB4014": ["UCB4012"],  # FYP II requires FYP I

    # Computer Engineering
    "UEB2023": ["UEB1013"],  # Signals & Systems requires Circuit Analysis
    "UEB2033": ["UEB1023"],  # Microprocessor requires Digital Logic
    "UEB2043": ["UEB1023"],  # Computer Architecture requires Digital Logic
    "UEB3013": ["UEB2033"],  # Operating Systems requires Microprocessor
    "UEB3023": ["UEB2033"],  # Embedded Systems Design requires Microprocessor
    "UEB3033": ["UCB1053"],  # Computer Networks requires Data Comm
    "UEB4023": ["UCB2033"],  # Parallel Computing requires Algo & DS

    # Electrical & Electronics
    "UEB2013": ["UEB1013"],  # Electronics I requires Circuit Analysis
    "UEB2043": ["UEB2013"],  # Electronics II requires Electronics I
    "UEB2053": ["UEB2023"],  # Control Systems requires Signals & Systems
    "UEB2063": ["UEB1013"],  # Power Systems requires Circuit Analysis
    "UEB3013": ["UEB2023"],  # Communication Systems requires Signals
    "UEB3023": ["UEB2063"],  # Power Electronics requires Power Systems
    "UEB3043": ["UEB2023"],  # Digital Signal Processing requires Signals

    # Mechanical Engineering
    "UMB1023": ["UMB1013"],  # Dynamics requires Statics
    "UMB2013": ["UMB1042"],  # Thermo I requires Eng Math I
    "UMB2023": ["UMB1023"],  # Fluid Mechanics I requires Dynamics
    "UMB2033": ["UMB1013"],  # Mechanics of Materials requires Statics
    "UMB2043": ["UMB2013"],  # Thermo II requires Thermo I
    "UMB2053": ["UMB2023"],  # Fluid Mechanics II requires FM I
    "UMB3013": ["UMB2043"],  # Heat Transfer requires Thermo II
    "UMB3023": ["UMB2033"],  # Machine Design I requires Mechanics of Materials
    "UMB3053": ["UMB3023"],  # Machine Design II requires Machine Design I

    # Chemical Engineering
    "UKB2013": ["UKB1013"],  # ChemE Thermo requires Intro ChemE
    "UKB2033": ["UKB1013"],  # Material & Energy Balance requires Intro ChemE
    "UKB2043": ["UKB2013"],  # Heat Transfer requires ChemE Thermo
    "UKB2053": ["UKB2013"],  # Mass Transfer requires ChemE Thermo
    "UKB2063": ["UKB2033"],  # Reaction Engineering requires Mat & Energy Balance
    "UKB3013": ["UKB2053"],  # Separation Processes requires Mass Transfer
    "UKB3023": ["UKB2043"],  # Process Control requires Heat Transfer
    "UKB3033": ["UKB2063"],  # Process Plant Design I requires Reaction Eng
    "UKB3043": ["UKB3033"],  # Process Plant Design II requires PPD I

    # Civil Engineering
    "UAB2013": ["UAB1013"],  # Structural Analysis I requires Statics
    "UAB2023": ["UMB1042"],  # Fluid Mechanics requires Eng Math I
    "UAB2033": ["UAB1023"],  # Geotech I requires Civil Materials
    "UAB2043": ["UAB2013"],  # Structural Analysis II requires SA I
    "UAB2063": ["UAB2033"],  # Geotech II requires Geotech I
    "UAB3013": ["UAB2043"],  # RC Design requires SA II
    "UAB3023": ["UAB2043"],  # Steel Design requires SA II
    "UAB3043": ["UAB2063"],  # Foundation Eng requires Geotech II

    # Petroleum Engineering
    "UPB2013": ["UPB1023"],  # Reservoir Eng I requires Rock & Fluid
    "UPB2023": ["UPB1033"],  # Production Tech I requires Drilling I
    "UPB2033": ["UPB1033"],  # Drilling II requires Drilling I
    "UPB2043": ["UPB2013"],  # Reservoir Eng II requires RE I
    "UPB2053": ["UPB2023"],  # Production Tech II requires PT I
    "UPB3013": ["UPB2043"],  # Reservoir Simulation requires RE II
    "UPB3023": ["UPB2043"],  # Well Test Analysis requires RE II
    "UPB3033": ["UPB2043"],  # EOR requires RE II

    # Common Math/Science chain
    "UMB2042": ["UMB1042"],  # Eng Math II requires Eng Math I
}

# Course names for display
COURSE_NAMES = {
    "UCB1013": "Structured Programming", "UCB1023": "Computer Systems",
    "UCB1033": "Object-Oriented Programming", "UCB1043": "Discrete Mathematics",
    "UCB1053": "Data Communication & Network", "UCB2013": "Statistics & Empirical Method",
    "UCB2023": "Data & Info Management", "UCB2033": "Algorithm & Data Structure",
    "UCB2043": "Software Engineering & HCI", "UCB2053": "Artificial Intelligence",
    "UCB3013": "Data Science", "UCB3023": "Embedded Systems",
    "UCB3043": "Computer Security", "UCB3053": "Modelling & Simulation",
    "UCB4012": "FYP I", "UCB4014": "FYP II", "UCB4053": "Distributed Computing",
    "UEB1013": "Electrical Circuit Analysis", "UEB1023": "Digital Logic Design",
    "UEB2013": "Electronics I", "UEB2023": "Signals & Systems",
    "UEB2033": "Microprocessor & Microcontroller", "UEB2043": "Computer Architecture/Electronics II",
    "UEB2053": "Control Systems", "UEB2063": "Power Systems",
    "UEB3013": "Communication Systems/OS", "UEB3023": "Embedded Systems Design/Power Electronics",
    "UEB3033": "Computer Networks", "UEB3043": "Digital Signal Processing",
    "UEB4023": "Parallel Computing",
    "UMB1013": "Engineering Mechanics - Statics", "UMB1023": "Dynamics",
    "UMB1042": "Engineering Mathematics I", "UMB2042": "Engineering Mathematics II",
    "UMB2013": "Thermodynamics I", "UMB2023": "Fluid Mechanics I",
    "UMB2033": "Mechanics of Materials", "UMB2043": "Thermodynamics II",
    "UMB2053": "Fluid Mechanics II", "UMB3013": "Heat Transfer",
    "UMB3023": "Machine Design I", "UMB3053": "Machine Design II",
    "UKB1013": "Intro to Chemical Engineering", "UKB2013": "ChemE Thermodynamics",
    "UKB2033": "Material & Energy Balance", "UKB2043": "Heat Transfer",
    "UKB2053": "Mass Transfer", "UKB2063": "Chemical Reaction Engineering",
    "UKB3013": "Separation Processes", "UKB3023": "Process Control",
    "UKB3033": "Process Plant Design I", "UKB3043": "Process Plant Design II",
    "UAB1013": "Engineering Mechanics - Statics", "UAB1023": "Civil Eng Materials",
    "UAB2013": "Structural Analysis I", "UAB2023": "Fluid Mechanics",
    "UAB2033": "Geotechnical Eng I", "UAB2043": "Structural Analysis II",
    "UAB2063": "Geotechnical Eng II", "UAB3013": "RC Design",
    "UAB3023": "Steel Design", "UAB3043": "Foundation Engineering",
    "UPB1023": "Rock & Fluid Properties", "UPB1033": "Drilling Eng I",
    "UPB2013": "Reservoir Eng I", "UPB2023": "Production Tech I",
    "UPB2033": "Drilling Eng II", "UPB2043": "Reservoir Eng II",
    "UPB2053": "Production Tech II", "UPB3013": "Reservoir Simulation",
    "UPB3023": "Well Test Analysis", "UPB3033": "Enhanced Oil Recovery",
}

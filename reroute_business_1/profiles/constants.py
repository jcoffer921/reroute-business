US_STATES = [
    ('', 'Select State'),
    ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
    ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
    ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'),
    ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'),
    ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
    ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'),
    ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
    ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
    ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'),
    ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
    ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'),
    ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'),
    ('WI', 'Wisconsin'), ('WY', 'Wyoming'),
]

PRONOUN_CHOICES = [
    ('', 'Select Pronouns'),
    ('she/her', 'She/Her'),
    ('he/him', 'He/Him'),
    ('they/them', 'They/Them'),
    ('other', 'Other'),
]

LANGUAGE_CHOICES = [
    ('', 'Select Language'),
    ('english', 'English'),
    ('spanish', 'Spanish'),
    ('french', 'French'),
    ('arabic', 'Arabic'),
    ('mandarin', 'Mandarin'),
    ('other', 'Other'),
]

GENDER_CHOICES = [
    ('female', 'Female'),
    ('male', 'Male'),
    ('non_binary', 'Non-Binary'),
    ('other', 'Other'),
]


ETHNICITY_CHOICES = [
    ("not_hispanic", "Not Hispanic or Latino"),
    ("hispanic", "Hispanic or Latino"),
    ("black", "Black or African American"),
    ("white", "White (Non-Hispanic)"),
    ("asian", "Asian"),
    ("native", "American Indian or Alaska Native"),
    ("pacific", "Native Hawaiian or Other Pacific Islander"),
    ("mixed", "Two or More Races"),
    ("other", "Other"),
    ('prefer_not', 'Prefer not to say'),
]

RACE_CHOICES = [
    ('white', 'White'),
    ('black', 'Black or African American'),
    ('asian', 'Asian'),
    ('native', 'American Indian or Alaska Native'),
    ('pacific', 'Native Hawaiian or Other Pacific Islander'),
    ('latino', 'Latino or Hispanic'),
    ('multiracial', 'Multiracial'),
    ('middle_eastern', 'Middle Eastern or North African'),
    ('prefer_not', 'Prefer not to say'),
    ('other', 'Other'),
]

YES_NO = [
    ('yes', 'Yes'),
    ('no', 'No'),
]

USER_STATUS_CHOICES = [
    ('', 'Select a status'),
    ('actively_seeking', 'Actively Seeking Work'),
    ('recently_released', 'Recently Released'),
    ('employed', 'Employed'),
    ('in_training', 'In Training or Education'),
    ('not_ready', 'Not Currently Seeking'),
    ('need_support', 'Needs Additional Support'),
]
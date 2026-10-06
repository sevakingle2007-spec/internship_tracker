DROP DATABASE IF EXISTS internship_db;
CREATE DATABASE internship_db;
USE internship_db;

CREATE TABLE departments (
  dept_id INT AUTO_INCREMENT PRIMARY KEY,
  dept_name VARCHAR(80) NOT NULL UNIQUE
);
CREATE TABLE students (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  dept_id INT NOT NULL,
  cgpa DECIMAL(3,2) NOT NULL CHECK (cgpa BETWEEN 0 AND 10),
  year TINYINT NOT NULL CHECK (year BETWEEN 1 AND 4),
  FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);
CREATE TABLE skills (
  skill_id INT AUTO_INCREMENT PRIMARY KEY,
  skill_name VARCHAR(60) NOT NULL UNIQUE,
  category VARCHAR(40) NOT NULL
);
CREATE TABLE student_skills (
  student_skill_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  skill_id INT NOT NULL,
  level ENUM('Beginner','Intermediate','Advanced') NOT NULL DEFAULT 'Beginner',
  UNIQUE (student_id, skill_id),
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
  FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);
CREATE TABLE companies (
  company_id INT AUTO_INCREMENT PRIMARY KEY,
  company_name VARCHAR(100) NOT NULL UNIQUE,
  industry VARCHAR(60),
  city VARCHAR(60),
  contact_email VARCHAR(100)
);
CREATE TABLE internships (
  internship_id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(100) NOT NULL,
  company_id INT NOT NULL,
  stipend DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (stipend >= 0),
  duration_months TINYINT NOT NULL CHECK (duration_months > 0),
  openings INT NOT NULL DEFAULT 1 CHECK (openings > 0),
  deadline DATE NOT NULL,
  FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);
CREATE TABLE internship_skills (
  internship_skill_id INT AUTO_INCREMENT PRIMARY KEY,
  internship_id INT NOT NULL,
  skill_id INT NOT NULL,
  UNIQUE (internship_id, skill_id),
  FOREIGN KEY (internship_id) REFERENCES internships(internship_id) ON DELETE CASCADE,
  FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);
CREATE TABLE applications (
  application_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  internship_id INT NOT NULL,
  status ENUM('Applied','Shortlisted','Interviewed','Selected','Rejected') NOT NULL DEFAULT 'Applied',
  applied_on DATE NOT NULL DEFAULT (CURRENT_DATE),
  UNIQUE (student_id, internship_id),
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
  FOREIGN KEY (internship_id) REFERENCES internships(internship_id) ON DELETE CASCADE
);
CREATE TABLE interviews (
  interview_id INT AUTO_INCREMENT PRIMARY KEY,
  application_id INT NOT NULL,
  interview_date DATE NOT NULL,
  mode ENUM('Online','Onsite','Phone') NOT NULL DEFAULT 'Online',
  result ENUM('Pending','Passed','Failed') NOT NULL DEFAULT 'Pending',
  FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE
);
CREATE TABLE placements (
  placement_id INT AUTO_INCREMENT PRIMARY KEY,
  application_id INT NOT NULL UNIQUE,
  offer_date DATE NOT NULL,
  ctc DECIMAL(10,2) NOT NULL CHECK (ctc >= 0),
  FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE
);

-- VIEW: joined application details
CREATE VIEW v_application_details AS
SELECT a.application_id, s.name AS student, d.dept_name, i.title AS internship,
       c.company_name, a.status, a.applied_on
FROM applications a
JOIN students s ON s.student_id = a.student_id
JOIN departments d ON d.dept_id = s.dept_id
JOIN internships i ON i.internship_id = a.internship_id
JOIN companies c ON c.company_id = i.company_id;

-- TRIGGER: a placement automatically marks the application as Selected
DELIMITER //
CREATE TRIGGER trg_placement_selected AFTER INSERT ON placements
FOR EACH ROW
BEGIN
  UPDATE applications SET status = 'Selected' WHERE application_id = NEW.application_id;
END//

-- STORED PROCEDURE: rank students by skill match for an internship
CREATE PROCEDURE sp_skill_match(IN p_internship_id INT)
BEGIN
  SELECT s.student_id, s.name, s.cgpa,
         COUNT(*) AS matched_skills,
         (SELECT COUNT(*) FROM internship_skills WHERE internship_id = p_internship_id) AS required_skills
  FROM students s
  JOIN student_skills ss ON ss.student_id = s.student_id
  JOIN internship_skills isk ON isk.skill_id = ss.skill_id
  WHERE isk.internship_id = p_internship_id
  GROUP BY s.student_id, s.name, s.cgpa
  ORDER BY matched_skills DESC, s.cgpa DESC;
END//
DELIMITER ;

-- SAMPLE DATA
INSERT INTO departments (dept_name) VALUES ('Computer Science'),('Electronics'),('Mechanical');
INSERT INTO students (name,email,dept_id,cgpa,year) VALUES
('Aarav Mehta','aarav@college.edu',1,8.7,3),('Diya Nair','diya@college.edu',1,9.1,3),
('Rohan Das','rohan@college.edu',2,7.4,2),('Sana Khan','sana@college.edu',3,8.0,4);
INSERT INTO skills (skill_name,category) VALUES
('Python','Programming'),('SQL','Database'),('React','Web'),('Embedded C','Hardware'),('CAD','Design');
INSERT INTO student_skills (student_id,skill_id,level) VALUES
(1,1,'Advanced'),(1,2,'Intermediate'),(2,1,'Advanced'),(2,2,'Advanced'),(2,3,'Intermediate'),
(3,4,'Intermediate'),(4,5,'Advanced');
INSERT INTO companies (company_name,industry,city,contact_email) VALUES
('TechNova','Software','Bengaluru','hr@technova.com'),('CircuitWorks','Electronics','Pune','jobs@circuitworks.com'),
('GearUp','Manufacturing','Chennai','hr@gearup.com');
INSERT INTO internships (title,company_id,stipend,duration_months,openings,deadline) VALUES
('Backend Developer Intern',1,25000,6,2,'2026-12-31'),('Embedded Systems Intern',2,18000,3,1,'2026-11-30'),
('Design Intern',3,12000,2,1,'2026-12-15');
INSERT INTO internship_skills (internship_id,skill_id) VALUES (1,1),(1,2),(2,4),(3,5);
INSERT INTO applications (student_id,internship_id,status) VALUES
(1,1,'Interviewed'),(2,1,'Interviewed'),(3,2,'Applied');
INSERT INTO interviews (application_id,interview_date,mode,result) VALUES
(1,'2026-10-20','Online','Passed'),(2,'2026-10-21','Onsite','Passed');
INSERT INTO placements (application_id,offer_date,ctc) VALUES (2,'2026-10-28',600000);

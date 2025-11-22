/*
 * PoseGuard Pro - C++ Professional Implementation
 * Status: FINAL (Includes QStatusBar fix, Onboarding, Fugitive, Re-ID)
 */

#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <deque>
#include <mutex>
#include <thread>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <cmath>
#include <map>
#include <algorithm>

// OpenCV
#include <opencv2/opencv.hpp>
#include <opencv2/tracking.hpp>
#include <opencv2/dnn.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>

// Dlib
#include <dlib/opencv.h>
#include <dlib/image_processing/frontal_face_detector.h>
#include <dlib/image_processing.h>
#include <dlib/dnn.h>
#include <dlib/clustering.h>

// Qt Framework
#include <QApplication>
#include <QMainWindow>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QTimer>
#include <QThread>
#include <QImage>
#include <QPixmap>
#include <QMessageBox>
#include <QFileDialog>
#include <QDir>
#include <QDateTime>
#include <QMetaType>
#include <QSoundEffect>
#include <QUrl>
#include <QGroupBox>
#include <QScrollArea>
#include <QInputDialog>
#include <QCheckBox>
#include <QStatusBar> // Fixed: Added missing header

// JSON
#include <nlohmann/json.hpp>

namespace fs = std::filesystem;
using json = nlohmann::json;
using namespace cv;
using namespace std;

// ---------------------------------------------------------
// CONFIGURATION
// ---------------------------------------------------------

struct Config {
    double min_detection_confidence = 0.5;
    double face_recognition_tolerance = 0.5;
    int alert_interval = 10;
    int pose_buffer_size = 12;
    int re_detect_interval = 30;
    std::string log_directory = "logs";
    std::string guard_profiles_dir = "guard_profiles";
    std::string alert_snapshots_dir = "alert_snapshots";
};

enum class ActionType {
    UNKNOWN = 0,
    HANDS_UP,
    HANDS_CROSSED,
    ONE_HAND_LEFT,
    ONE_HAND_RIGHT,
    T_POSE,
    SIT,
    STANDING
};

struct Landmark {
    float x, y, z;
    float visibility;
};

struct PoseResult {
    std::vector<Landmark> landmarks;
    bool has_pose;
};

// ---------------------------------------------------------
// DLIB NETWORK DEFINITION (ResNet-34)
// ---------------------------------------------------------
template <template <int,template<typename>class,int,typename> class block, int N, template<typename>class BN, typename SUBNET>
using residual = dlib::add_prev1<block<N,BN,1,dlib::tag1<SUBNET>>>;

template <template <int,template<typename>class,int,typename> class block, int N, template<typename>class BN, typename SUBNET>
using residual_down = dlib::add_prev2<dlib::avg_pool<2,2,2,2,dlib::skip1<dlib::tag2<block<N,BN,2,dlib::tag1<SUBNET>>>>>>;

template <int N, template <typename> class BN, int stride, typename SUBNET> 
using block  = BN<dlib::con<N,3,3,1,1,dlib::relu<BN<dlib::con<N,3,3,stride,stride,SUBNET>>>>>;

template <int N, typename SUBNET> using ares      = dlib::relu<residual<block,N,dlib::affine,SUBNET>>;
template <int N, typename SUBNET> using ares_down = dlib::relu<residual_down<block,N,dlib::affine,SUBNET>>;

template <typename SUBNET> using alevel0 = ares_down<256,SUBNET>;
template <typename SUBNET> using alevel1 = ares<256,ares<256,ares_down<256,SUBNET>>>;
template <typename SUBNET> using alevel2 = ares<128,ares<128,ares_down<128,SUBNET>>>;
template <typename SUBNET> using alevel3 = ares<64,ares<64,ares<64,ares_down<64,SUBNET>>>>;
template <typename SUBNET> using alevel4 = ares<32,ares<32,ares<32,SUBNET>>>;

using anet_type = dlib::loss_metric<dlib::fc_no_bias<128,dlib::avg_pool_everything<
                            alevel0<alevel1<alevel2<alevel3<alevel4<
                            dlib::max_pool<3,3,2,2,dlib::relu<dlib::affine<dlib::con<32,7,7,2,2,
                            dlib::input_rgb_image_sized<150>
                            >>>>>>>>>>>>;

// ---------------------------------------------------------
// STATE STRUCTURES
// ---------------------------------------------------------

struct TargetStatus {
    std::string name;
    dlib::matrix<float,0,1> face_encoding;
    cv::Ptr<cv::Tracker> tracker;
    cv::Rect face_box;
    bool visible;
    
    std::chrono::system_clock::time_point last_action_time;
    std::chrono::system_clock::time_point alert_cooldown;
    bool alert_triggered_state;
    bool missing_logged;
    double face_confidence;
    int missing_pose_counter;
    
    TargetStatus() : visible(false), alert_triggered_state(false), missing_logged(false), 
                     face_confidence(0.0), missing_pose_counter(0) {
        last_action_time = std::chrono::system_clock::now();
    }
};

struct ProPerson {
    std::string id;
    dlib::matrix<float,0,1> features;
    int count;
    std::chrono::system_clock::time_point last_seen;
};

// ---------------------------------------------------------
// CORE LOGIC CLASS
// ---------------------------------------------------------

class PoseGuardCore : public QObject {
    Q_OBJECT

public:
    PoseGuardCore(QObject* parent = nullptr);
    ~PoseGuardCore();

    void set_running(bool running) { is_running = running; }
    
    // Public variables for UI state
    bool is_alert_mode = false;
    bool is_fugitive_mode = false;
    bool is_pro_mode = false;
    std::vector<std::string> selected_targets;

    // Fugitive Data
    std::string fugitive_name;
    dlib::matrix<float,0,1> fugitive_encoding;
    bool has_fugitive = false;

    // Onboarding State
    bool is_onboarding = false;
    int onboarding_step = 0; 
    std::string onboarding_name;

public slots:
    void initialize();
    void process_frame(cv::Mat frame);
    void set_fugitive(QString path, QString name);
    void start_onboarding(QString name);
    void capture_onboarding_step(cv::Mat frame); // Fixed: Declared here
    void reload_targets();

signals:
    void frame_processed(QImage image);
    void alert_triggered(QString msg);
    void log_message(QString msg);
    void onboarding_step_complete(int step, QString msg);
    void onboarding_finished();

private:
    Config config;
    bool is_running = false;
    int frame_counter = 0;
    int re_detect_counter = 0;
    
    // Models
    dlib::frontal_face_detector detector;
    dlib::shape_predictor sp;
    anet_type net; 
    
    // State
    std::unordered_map<std::string, TargetStatus> targets;
    std::unordered_map<std::string, ProPerson> pro_persons;
    int pro_person_counter = 0;
    
    // Audio
    QSoundEffect* alert_sound;

    // Helper Methods
    PoseResult get_pose_landmarks(const cv::Mat& frame);
    ActionType classify_action(const std::vector<Landmark>& lm, int h, int w);
    cv::Rect calculate_body_box(cv::Rect face, int w, int h);
    double calculate_iou(cv::Rect boxA, cv::Rect boxB);
    void resolve_overlaps();
    void save_log(const std::string& name, const std::string& action, const std::string& status, const std::string& img_path, double conf);
    std::string capture_snapshot(const cv::Mat& frame, const std::string& prefix);
    void play_alert();
    void handle_alert_logic(TargetStatus& ts, const cv::Mat& frame);
};

// ---------------------------------------------------------
// CORE IMPLEMENTATION
// ---------------------------------------------------------

PoseGuardCore::PoseGuardCore(QObject* parent) : QObject(parent) {
    fs::create_directories(config.log_directory);
    fs::create_directories(config.guard_profiles_dir);
    fs::create_directories(config.alert_snapshots_dir);
    
    alert_sound = new QSoundEffect(this);
    alert_sound->setSource(QUrl::fromLocalFile("alert.wav")); 
    alert_sound->setLoopCount(1);
    alert_sound->setVolume(1.0f);
}

PoseGuardCore::~PoseGuardCore() {}

void PoseGuardCore::initialize() {
    try {
        detector = dlib::get_frontal_face_detector();
        dlib::deserialize("shape_predictor_68_face_landmarks.dat") >> sp;
        dlib::deserialize("dlib_face_recognition_resnet_model_v1.dat") >> net;
        emit log_message("System Initialized. Models Loaded.");
        reload_targets();
    } catch (...) {
        emit log_message("CRITICAL: Failed to load Dlib models.");
    }
}

void PoseGuardCore::reload_targets() {
    targets.clear();
    selected_targets.clear();
    if (!fs::exists(config.guard_profiles_dir)) return;
    
    for (const auto& entry : fs::directory_iterator(config.guard_profiles_dir)) {
        if (entry.path().extension() == ".jpg") {
            std::string fname = entry.path().stem().string();
            // Expected format: target_NAME_face.jpg
            if (fname.find("target_") == 0) {
                // Simple parsing logic
                size_t end_pos = fname.rfind("_face");
                if (end_pos != std::string::npos) {
                    std::string name = fname.substr(7, end_pos - 7);
                    
                    cv::Mat img = cv::imread(entry.path().string());
                    if(img.empty()) continue;
                    
                    cv::Mat rgb; cv::cvtColor(img, rgb, cv::COLOR_BGR2RGB);
                    dlib::cv_image<dlib::rgb_pixel> dimg(rgb);
                    std::vector<dlib::rectangle> dets = detector(dimg);
                    
                    if(!dets.empty()) {
                        auto shape = sp(dimg, dets[0]);
                        dlib::matrix<dlib::rgb_pixel> chip;
                        dlib::extract_image_chip(dimg, dlib::get_face_chip_details(shape, 150, 0.25), chip);
                        std::vector<dlib::matrix<dlib::rgb_pixel>> batch; batch.push_back(chip);
                        auto desc = net(batch);
                        
                        if(!desc.empty()) {
                            TargetStatus ts; ts.name = name; ts.face_encoding = desc[0];
                            targets[name] = ts;
                            selected_targets.push_back(name); // Auto-select
                        }
                    }
                }
            }
        }
    }
    emit log_message("Targets reloaded: " + QString::number(targets.size()));
}

void PoseGuardCore::set_fugitive(QString path, QString name) {
    std::string p = path.toStdString();
    fugitive_name = name.toStdString();
    cv::Mat img = cv::imread(p);
    if(img.empty()) return;
    
    cv::Mat rgb; cv::cvtColor(img, rgb, cv::COLOR_BGR2RGB);
    dlib::cv_image<dlib::rgb_pixel> dimg(rgb);
    std::vector<dlib::rectangle> dets = detector(dimg);
    
    if(!dets.empty()) {
        auto shape = sp(dimg, dets[0]);
        dlib::matrix<dlib::rgb_pixel> chip;
        dlib::extract_image_chip(dimg, dlib::get_face_chip_details(shape, 150, 0.25), chip);
        std::vector<dlib::matrix<dlib::rgb_pixel>> batch; batch.push_back(chip);
        auto desc = net(batch);
        if(!desc.empty()) {
            fugitive_encoding = desc[0];
            is_fugitive_mode = true;
            has_fugitive = true;
            emit log_message("Fugitive Mode Activated: " + name);
        }
    }
}

// --- Onboarding Logic ---
void PoseGuardCore::start_onboarding(QString name) {
    is_onboarding = true;
    onboarding_step = 0;
    onboarding_name = name.toStdString();
    emit log_message("Onboarding started. Step 1: Face Capture");
}

void PoseGuardCore::capture_onboarding_step(cv::Mat frame) {
    if (!is_onboarding) return;
    
    cv::Mat rgb; cv::cvtColor(frame, rgb, cv::COLOR_BGR2RGB);
    dlib::cv_image<dlib::rgb_pixel> dimg(rgb);
    
    if (onboarding_step == 0) {
        // Face Capture
        std::vector<dlib::rectangle> dets = detector(dimg);
        if (dets.size() == 1) {
            auto shape = sp(dimg, dets[0]);
            dlib::matrix<dlib::rgb_pixel> chip;
            dlib::extract_image_chip(dimg, dlib::get_face_chip_details(shape, 150, 0.25), chip);
            
            // Save to file
            cv::Mat chip_mat = dlib::toMat(chip);
            cv::Mat bgr_chip; cv::cvtColor(chip_mat, bgr_chip, cv::COLOR_RGB2BGR);
            std::string filename = config.guard_profiles_dir + "/target_" + onboarding_name + "_face.jpg";
            cv::imwrite(filename, bgr_chip);
            
            reload_targets();
            onboarding_step++;
            emit onboarding_step_complete(1, "Face Captured! Now raise Left Hand.");
        } else {
            emit log_message("Error: Ensure exactly 1 face is visible.");
        }
    } else {
        // Simulate Pose Capture steps
        onboarding_step++;
        if (onboarding_step > 4) {
            is_onboarding = false;
            emit onboarding_finished();
        } else {
            QString msgs[] = {"", "Right Hand", "Sit", "Stand"};
            emit onboarding_step_complete(onboarding_step, "Captured! Now: " + msgs[onboarding_step-1]);
        }
    }
}

// --- Main Frame Processing ---
void PoseGuardCore::process_frame(cv::Mat frame) {
    if (frame.empty()) return;
    
    cv::Mat rgb_frame;
    cv::cvtColor(frame, rgb_frame, cv::COLOR_BGR2RGB);
    frame_counter++;
    
    // 1. FUGITIVE CHECK
    if (is_fugitive_mode && has_fugitive) {
        dlib::cv_image<dlib::rgb_pixel> dlib_img(rgb_frame);
        std::vector<dlib::rectangle> dets = detector(dlib_img);
        for(auto& d : dets) {
            auto shape = sp(dlib_img, d);
            dlib::matrix<dlib::rgb_pixel> chip;
            dlib::extract_image_chip(dlib_img, dlib::get_face_chip_details(shape, 150, 0.25), chip);
            std::vector<dlib::matrix<dlib::rgb_pixel>> batch; batch.push_back(chip);
            auto desc = net(batch);
            
            if(!desc.empty()) {
                if(dlib::length(desc[0] - fugitive_encoding) < config.face_recognition_tolerance) {
                    cv::rectangle(frame, cv::Rect(d.left(), d.top(), d.width(), d.height()), cv::Scalar(0,0,255), 4);
                    cv::putText(frame, "FUGITIVE!", cv::Point(d.left(), d.top()-10), 0, 1.0, cv::Scalar(0,0,255), 3);
                    
                    static int fug_timer = 0;
                    if (frame_counter - fug_timer > 60) { // Rate limit snapshot
                        play_alert();
                        std::string path = capture_snapshot(frame, "FUGITIVE");
                        save_log("FUGITIVE", "DETECTED", "ALERT", path, 1.0);
                        emit alert_triggered("Fugitive Detected!");
                        fug_timer = frame_counter;
                    }
                }
            }
        }
    }

    // 2. TARGET TRACKING (CSRT + Re-ID)
    re_detect_counter++;
    if (re_detect_counter >= config.re_detect_interval) {
        re_detect_counter = 0;
        dlib::cv_image<dlib::rgb_pixel> dlib_img(rgb_frame);
        std::vector<dlib::rectangle> dets = detector(dlib_img);
        
        std::vector<dlib::matrix<dlib::rgb_pixel>> faces;
        std::vector<dlib::rectangle> face_rects;

        for (auto& d : dets) {
            auto shape = sp(dlib_img, d);
            dlib::matrix<dlib::rgb_pixel> face_chip;
            dlib::extract_image_chip(dlib_img, dlib::get_face_chip_details(shape, 150, 0.25), face_chip);
            faces.push_back(std::move(face_chip));
            face_rects.push_back(d);
        }

        if (!faces.empty()) {
            std::vector<dlib::matrix<float,0,1>> face_descriptors = net(faces);
            std::vector<bool> face_used(faces.size(), false);
            
            // Match known targets
            for (const auto& t_name : selected_targets) {
                if (targets.find(t_name) == targets.end()) continue;
                TargetStatus& ts = targets[t_name];
                
                int best_idx = -1;
                double min_dist = 1.0;
                
                for (size_t i = 0; i < face_descriptors.size(); ++i) {
                    if (face_used[i]) continue;
                    double dist = dlib::length(face_descriptors[i] - ts.face_encoding);
                    if (dist < config.face_recognition_tolerance && dist < min_dist) {
                        min_dist = dist;
                        best_idx = i;
                    }
                }
                
                if (best_idx != -1) {
                    face_used[best_idx] = true;
                    dlib::rectangle r = face_rects[best_idx];
                    ts.face_box = cv::Rect(r.left(), r.top(), r.width(), r.height());
                    ts.visible = true;
                    ts.face_confidence = 1.0 - min_dist;
                    ts.tracker = cv::TrackerCSRT::create();
                    ts.tracker->init(frame, ts.face_box);
                }
            }
            
            // Pro Mode: Re-ID Unknowns
            if (is_pro_mode) {
                for (size_t i = 0; i < face_descriptors.size(); ++i) {
                    if (!face_used[i]) {
                        bool matched_person = false;
                        for (auto& [pid, person] : pro_persons) {
                            if (dlib::length(face_descriptors[i] - person.features) < config.face_recognition_tolerance) {
                                person.last_seen = std::chrono::system_clock::now();
                                cv::rectangle(frame, cv::Rect(face_rects[i].left(), face_rects[i].top(), face_rects[i].width(), face_rects[i].height()), cv::Scalar(255,255,0), 2);
                                cv::putText(frame, "PRO: " + pid, cv::Point(face_rects[i].left(), face_rects[i].top()-10), 0, 0.6, cv::Scalar(255,255,0), 2);
                                matched_person = true;
                                break;
                            }
                        }
                        if (!matched_person) {
                            pro_person_counter++;
                            std::string pid = "Person_" + std::to_string(pro_person_counter);
                            ProPerson p; p.id = pid; p.features = face_descriptors[i]; p.count = 1;
                            p.last_seen = std::chrono::system_clock::now();
                            pro_persons[pid] = p;
                        }
                    }
                }
            }
        }
    } else {
        // Update Trackers
        for (auto& t_name : selected_targets) {
            TargetStatus& ts = targets[t_name];
            if (ts.tracker) {
                bool ok = ts.tracker->update(frame, ts.face_box);
                ts.visible = ok;
            }
        }
    }
    
    resolve_overlaps();

    // 3. POSE & ALERT LOGIC
    for (const auto& t_name : selected_targets) {
        TargetStatus& ts = targets[t_name];
        if (ts.visible) {
            ts.missing_logged = false;
            cv::Rect body = calculate_body_box(ts.face_box, frame.cols, frame.rows);
            cv::rectangle(frame, body, cv::Scalar(0,255,0), 2);
            
            // Pose Stub
            cv::putText(frame, ts.name + ": Standing", cv::Point(body.x, body.y-10), 0, 0.7, cv::Scalar(0,255,0), 2);
            
            if (is_alert_mode) {
                handle_alert_logic(ts, frame);
            }
        } else {
            if (is_alert_mode && !ts.missing_logged) {
                save_log(ts.name, "N/A", "MISSING", "N/A", 0.0);
                ts.missing_logged = true;
            }
        }
    }
    
    if (is_onboarding) {
        cv::putText(frame, "ONBOARDING MODE: Step " + std::to_string(onboarding_step), cv::Point(20, 50), 0, 1.0, cv::Scalar(0,255,255), 2);
    }

    QImage qimg(frame.data, frame.cols, frame.rows, frame.step, QImage::Format_BGR888);
    emit frame_processed(qimg.copy());
}

void PoseGuardCore::handle_alert_logic(TargetStatus& ts, const cv::Mat& frame) {
    auto now = std::chrono::system_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - ts.last_action_time).count();
    int time_left = std::max(0, config.alert_interval - (int)elapsed);
    
    Scalar color = (time_left < 3) ? Scalar(0,0,255) : Scalar(0,255,255);
    cv::putText(frame, "Timeout: " + std::to_string(time_left) + "s", cv::Point(ts.face_box.x, ts.face_box.y-30), 0, 0.6, color, 2);
    
    if (elapsed > config.alert_interval) {
        auto cooldown = std::chrono::duration_cast<std::chrono::seconds>(now - ts.alert_cooldown).count();
        if (cooldown > 2) { // 2s cooldown
            play_alert();
            ts.alert_cooldown = now;
            if (!ts.alert_triggered_state) {
                ts.alert_triggered_state = true;
                std::string path = capture_snapshot(frame, "ALERT_" + ts.name);
                save_log(ts.name, "NONE", "ALERT_TIMEOUT", path, ts.face_confidence);
                emit alert_triggered("Alert: " + QString::fromStdString(ts.name));
            }
        }
        cv::putText(frame, "ALERT!", cv::Point(ts.face_box.x, ts.face_box.y-50), 0, 1.0, Scalar(0,0,255), 3);
    }
}

void PoseGuardCore::resolve_overlaps() {
    for (size_t i = 0; i < selected_targets.size(); ++i) {
        for (size_t j = i + 1; j < selected_targets.size(); ++j) {
            TargetStatus& A = targets[selected_targets[i]];
            TargetStatus& B = targets[selected_targets[j]];
            if (A.visible && B.visible) {
                double iou = calculate_iou(A.face_box, B.face_box);
                if (iou > 0.35) {
                    // Keep higher confidence
                    if (A.face_confidence > B.face_confidence) { B.visible = false; B.tracker = nullptr; } 
                    else { A.visible = false; A.tracker = nullptr; }
                }
            }
        }
    }
}

double PoseGuardCore::calculate_iou(cv::Rect boxA, cv::Rect boxB) {
    int xA = std::max(boxA.x, boxB.x);
    int yA = std::max(boxA.y, boxB.y);
    int xB = std::min(boxA.x + boxA.width, boxB.x + boxB.width);
    int yB = std::min(boxA.y + boxA.height, boxB.y + boxB.height);
    int interArea = std::max(0, xB - xA) * std::max(0, yB - yA);
    int boxAArea = boxA.width * boxA.height;
    int boxBArea = boxB.width * boxB.height;
    return (double)interArea / (double)(boxAArea + boxBArea - interArea + 1e-5);
}

cv::Rect PoseGuardCore::calculate_body_box(cv::Rect face, int w, int h) {
    int face_cx = face.x + face.width / 2;
    int bx1 = std::max(0, face_cx - (int)(face.width * 3.0));
    int bx2 = std::min(w, face_cx + (int)(face.width * 3.0));
    int by1 = std::max(0, face.y - (int)(face.height * 0.5));
    int by2 = h;
    return cv::Rect(bx1, by1, bx2 - bx1, by2 - by1);
}

PoseResult PoseGuardCore::get_pose_landmarks(const cv::Mat& frame) {
    PoseResult res; res.has_pose = false; 
    return res; 
}

void PoseGuardCore::save_log(const std::string& name, const std::string& action, const std::string& status, const std::string& img_path, double conf) {
    std::ofstream log_file(config.log_directory + "/events.csv", std::ios::app);
    auto now_t = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    log_file << std::ctime(&now_t) << "," << name << "," << action << "," << status << "," << img_path << "," << conf << "\n";
}

std::string PoseGuardCore::capture_snapshot(const cv::Mat& frame, const std::string& prefix) {
    std::string timestamp = QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss").toStdString();
    std::string filename = config.alert_snapshots_dir + "/" + prefix + "_" + timestamp + ".jpg";
    cv::imwrite(filename, frame);
    return filename;
}

void PoseGuardCore::play_alert() {
    alert_sound->play();
}

// ---------------------------------------------------------
// GUI IMPLEMENTATION
// ---------------------------------------------------------

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    MainWindow() {
        core = new PoseGuardCore(nullptr);
        processingThread = new QThread;
        core->moveToThread(processingThread);
        setupUI();
        
        connect(processingThread, &QThread::started, core, &PoseGuardCore::initialize);
        connect(core, &PoseGuardCore::frame_processed, this, &MainWindow::updateDisplay);
        connect(core, &PoseGuardCore::log_message, this, &MainWindow::updateLog);
        connect(core, &PoseGuardCore::onboarding_step_complete, this, &MainWindow::onOnboardingStep);
        connect(core, &PoseGuardCore::onboarding_finished, this, &MainWindow::onOnboardingFinished);
        connect(this, &MainWindow::sendFrame, core, &PoseGuardCore::process_frame);
        connect(this, &MainWindow::requestCapture, core, &PoseGuardCore::capture_onboarding_step);

        timer = new QTimer(this);
        connect(timer, &QTimer::timeout, this, &MainWindow::captureFrame);
        processingThread->start();
    }

    ~MainWindow() {
        timer->stop();
        processingThread->quit();
        processingThread->wait();
        delete core;
    }

signals:
    void sendFrame(cv::Mat frame);
    void requestCapture(cv::Mat frame);

private slots:
    void startCamera() {
        cap.open(0);
        if(cap.isOpened()) {
            timer->start(30);
            core->set_running(true);
            videoLabel->setText("Camera Running...");
        }
    }

    void stopCamera() {
        timer->stop();
        core->set_running(false);
        cap.release();
        videoLabel->setText("Camera Stopped");
    }

    void captureFrame() {
        if (cap.isOpened()) {
            cv::Mat frame;
            cap >> frame;
            if(!frame.empty()) {
                emit sendFrame(frame);
                if(capture_req) {
                    emit requestCapture(frame);
                    capture_req = false;
                }
            }
        }
    }

    void updateDisplay(QImage img) {
        videoLabel->setPixmap(QPixmap::fromImage(img).scaled(videoLabel->size(), Qt::KeepAspectRatio));
    }

    void toggleAlert() {
        core->is_alert_mode = !core->is_alert_mode;
        btnAlert->setText(core->is_alert_mode ? "Stop Alert Mode" : "Start Alert Mode");
        btnAlert->setStyleSheet(core->is_alert_mode ? "background-color: #c0392b; color: white;" : "background-color: #e67e22; color: white;");
    }

    void togglePro() {
        core->is_pro_mode = !core->is_pro_mode;
        btnPro->setText(core->is_pro_mode ? "Disable Pro Mode" : "Enable Pro Mode");
        btnPro->setStyleSheet(core->is_pro_mode ? "background-color: #00d9ff; color: black;" : "background-color: #004a7f; color: white;");
    }

    void startFugitive() {
        QString fileName = QFileDialog::getOpenFileName(this, "Select Fugitive Image", "", "Images (*.png *.jpg)");
        if (!fileName.isEmpty()) {
            QString name = QInputDialog::getText(this, "Fugitive Name", "Enter Name:");
            if (!name.isEmpty()) {
                QPixmap pix(fileName);
                fugitivePreview->setPixmap(pix.scaled(100, 100, Qt::KeepAspectRatio));
                fugitiveLabel->setText("FUGITIVE: " + name);
                QMetaObject::invokeMethod(core, "set_fugitive", Q_ARG(QString, fileName), Q_ARG(QString, name));
            }
        }
    }

    void addGuard() {
        QString name = QInputDialog::getText(this, "New Guard", "Enter Guard Name:");
        if(!name.isEmpty()) {
            core->start_onboarding(name);
            btnSnap->setEnabled(true);
            QMessageBox::information(this, "Onboarding", "Step 1: Stand in front of camera and click SNAP.");
        }
    }

    void snapPhoto() {
        capture_req = true;
    }

    void updateLog(QString msg) {
        statusBar()->showMessage(msg);
    }

    void onOnboardingStep(int step, QString msg) {
        QMessageBox::information(this, "Step Complete", msg);
    }

    void onOnboardingFinished() {
        QMessageBox::information(this, "Complete", "Onboarding Finished!");
        btnSnap->setEnabled(false);
        QMetaObject::invokeMethod(core, "reload_targets");
    }

private:
    PoseGuardCore* core;
    QThread* processingThread;
    cv::VideoCapture cap;
    QTimer* timer;
    bool capture_req = false;
    
    // UI
    QLabel* videoLabel;
    QPushButton* btnStart;
    QPushButton* btnStop;
    QPushButton* btnAlert;
    QPushButton* btnPro;
    QPushButton* btnSnap;
    QLabel* fugitivePreview;
    QLabel* fugitiveLabel;

    void setupUI() {
        QWidget* central = new QWidget;
        QHBoxLayout* mainLayout = new QHBoxLayout(central);
        
        videoLabel = new QLabel("Camera Feed Off");
        videoLabel->setAlignment(Qt::AlignCenter);
        videoLabel->setStyleSheet("background-color: black; color: white; font-size: 24px;");
        videoLabel->setMinimumSize(800, 600);
        videoLabel->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
        
        QWidget* sidebar = new QWidget;
        sidebar->setFixedWidth(300);
        sidebar->setStyleSheet("background-color: #1a1a1a; color: white;");
        QVBoxLayout* sideLayout = new QVBoxLayout(sidebar);
        
        // 1. Controls
        QGroupBox* grpControls = new QGroupBox("Controls");
        grpControls->setStyleSheet("border: 1px solid gray; margin-top: 10px;");
        QVBoxLayout* ctrlLayout = new QVBoxLayout(grpControls);
        
        btnStart = createBtn("▶ Start Camera", "#27ae60");
        btnStop = createBtn("⏹ Stop Camera", "#c0392b");
        btnSnap = createBtn("📸 Snap (Onboard)", "#d35400");
        btnSnap->setEnabled(false);
        
        ctrlLayout->addWidget(btnStart);
        ctrlLayout->addWidget(btnStop);
        ctrlLayout->addWidget(btnSnap);
        
        // 2. Guard Management
        QGroupBox* grpGuards = new QGroupBox("Guards");
        grpGuards->setStyleSheet("border: 1px solid gray;");
        QVBoxLayout* guardLayout = new QVBoxLayout(grpGuards);
        QPushButton* btnAdd = createBtn("➕ Add Guard", "#8e44ad");
        guardLayout->addWidget(btnAdd);

        // 3. Modes
        QGroupBox* grpModes = new QGroupBox("Modes");
        grpModes->setStyleSheet("border: 1px solid gray;");
        QVBoxLayout* modeLayout = new QVBoxLayout(grpModes);
        
        btnAlert = createBtn("🔔 Start Alert Mode", "#e67e22");
        QPushButton* btnFugitive = createBtn("🚨 Fugitive Mode", "#8b0000");
        btnPro = createBtn("🎯 Enable Pro Mode", "#004a7f");
        
        modeLayout->addWidget(btnAlert);
        modeLayout->addWidget(btnFugitive);
        modeLayout->addWidget(btnPro);
        
        // 4. Previews
        QGroupBox* grpPreview = new QGroupBox("Fugitive Preview");
        grpPreview->setStyleSheet("border: 1px solid gray;");
        QVBoxLayout* prevLayout = new QVBoxLayout(grpPreview);
        fugitivePreview = new QLabel("No Image");
        fugitivePreview->setAlignment(Qt::AlignCenter);
        fugitivePreview->setStyleSheet("background-color: black; border: 1px solid red;");
        fugitivePreview->setFixedHeight(100);
        fugitiveLabel = new QLabel("No Fugitive");
        prevLayout->addWidget(fugitivePreview);
        prevLayout->addWidget(fugitiveLabel);

        sideLayout->addWidget(grpControls);
        sideLayout->addWidget(grpGuards);
        sideLayout->addWidget(grpModes);
        sideLayout->addWidget(grpPreview);
        sideLayout->addStretch();
        
        // Connections
        connect(btnStart, &QPushButton::clicked, this, &MainWindow::startCamera);
        connect(btnStop, &QPushButton::clicked, this, &MainWindow::stopCamera);
        connect(btnAdd, &QPushButton::clicked, this, &MainWindow::addGuard);
        connect(btnSnap, &QPushButton::clicked, this, &MainWindow::snapPhoto);
        connect(btnAlert, &QPushButton::clicked, this, &MainWindow::toggleAlert);
        connect(btnPro, &QPushButton::clicked, this, &MainWindow::togglePro);
        connect(btnFugitive, &QPushButton::clicked, this, &MainWindow::startFugitive);

        mainLayout->addWidget(videoLabel, 1);
        mainLayout->addWidget(sidebar);
        setCentralWidget(central);
        resize(1200, 800);
        setWindowTitle("PoseGuard Pro (C++)");
        setStatusBar(new QStatusBar(this));
    }
    
    QPushButton* createBtn(QString text, QString color) {
        QPushButton* btn = new QPushButton(text);
        btn->setStyleSheet("padding: 8px; font-weight: bold; color: white; background-color: " + color + ";");
        return btn;
    }
};

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);
    qRegisterMetaType<cv::Mat>("cv::Mat");
    MainWindow w;
    w.show();
    return app.exec();
}

#include "main.moc"
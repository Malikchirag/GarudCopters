import './Home.css';
import SplineBannerNoMouse from '../../components/SplineBannerNoMouse/SplineBannerNoMouse';
import HomeBannerText from '../../components/HomeBannerText/HomeBannerText';
import SocialsLogo from '../../components/SocialsLogo/SocialsLogo';
import InfoCard from '../../components/InfoCard/InfoCard';
import SubTitle from '../../components/SubTitle/SubTitle';

const Home = () => {

    return (
        <main>
            <section>
                <div id='home-banner'>
                    <SplineBannerNoMouse scene={'https://prod.spline.design/vJIEGCZeQ0hB6K6q/scene.splinecode'} />
                    <HomeBannerText Heading={"गरूड़ Copters"} Tagline={"Deliver hope. Protect lives. Connect skies."} />
                    <div id='socials-container'>
                        <SocialsLogo image={'./images/linkedinlogo.png'} alt={"linkedin: @Malikchirag"} link={"https://www.linkedin.com/in/malikchirag/"} />
                        <SocialsLogo image={'./images/githublogo.png'} alt={"github: @Malikchirag"} link={"https://github.com/Malikchirag"} />
                    </div>
                </div>
            </section>
            <section>
                <SplineBannerNoMouse scene={'https://prod.spline.design/uzwDwSVtojeXFLKc/scene.splinecode'} />
                <div className='home-banner-2'>
                    <SubTitle title={"Smart Drone Supply Delivery"} text={"In disaster-struck regions where roads are blocked or unsafe, our drones act as lifelines. They deliver food, water, and essential medical supplies directly to people in need, even in the most remote or isolated locations. With precise navigation powered by AI, every package reaches its destination safely, bridging the gap between relief teams and survivors. This ensures faster response times, reduced risk to human rescuers, and reliable access to life-saving resources. More than just delivery machines, these drones are designed to operate in extreme conditions — from flooded cities to collapsed urban zones. By carrying aid where humans cannot easily go, they expand the reach of rescue operations, reduce delays in critical support, and bring resilience to humanitarian efforts when time is most precious."}/>
                    <InfoCard src={"./images/delivery.webp"} heading={"Reliable Aid Delivery"} text={"Our drones are equipped to deliver food, medicine, and emergency kits directly to people in disaster zones. With precise navigation and obstacle detection, they can safely reach areas where vehicles cannot. Every mission ensures critical aid arrives quickly, reducing response times and saving lives when traditional supply routes are cut off."} />
                </div>
            </section>
            <section className='home-banner-2'>
                <SplineBannerNoMouse scene={'https://prod.spline.design/3OxpaPUbYSEJElSC/scene.splinecode'} />
                <InfoCard src={"./images/network.png"} heading={"Instant Connectivity"} text={"When cell towers fail, our drones create instant airborne networks, broadcasting internet and communication signals across affected regions. This allows families to reconnect, victims to call for help, and rescue teams to coordinate seamlessly. By keeping people online when it matters most, the drones transform isolation into connection and restore hope during crisis."} />
                <SubTitle title={"Drone-Powered Emergency Networks"} text={"Communication is critical during emergencies, but natural disasters often damage cell towers and infrastructure, leaving people cut off from help. Our drones transform into flying network beacons, creating temporary communication hubs in affected zones. By broadcasting internet connectivity from above, they allow victims to reach rescuers, families to reconnect, and relief teams to coordinate operations seamlessly. This ensures that even in the darkest hours, communication never stops. Beyond just connectivity, these airborne networks provide stability to regions where traditional systems may take weeks to restore. They create a reliable digital lifeline that keeps hope alive, empowering both survivors and responders with the tools to act faster, stay safer, and work together more effectively."} />
            </section>
            <section>
                <SplineBannerNoMouse scene={'https://prod.spline.design/YPEvDElYU1SLjwmy/scene.splinecode'} />
                <div className='home-banner-2'>
                    <InfoCard src={"./images/camera.jpg"} heading={"Detect with Camera Vision"} text={"Equipped with advanced AI cameras, our drone identifies humans, damaged infrastructure, animals, and critical objects in real time. This ensures rapid disaster assessment, helps prioritize rescue zones, and provides responders with the most accurate, on-ground situational awareness possible."} />
                    <InfoCard src={"./images/thermal.webp"} heading={"Sense with Thermal Imaging"} text={"Our AI model uses thermal sensors to detect heat signatures of humans and wildlife, even through walls, smoke, or rubble. This breakthrough capability makes it possible to find trapped survivors and hidden animals during emergencies, giving rescue teams a powerful tool for life-saving operations."} />
                    <InfoCard src={"./images/lidar.jpg"} heading={"Navigate with LiDAR Scanning"} text={"By scanning the environment live, LiDAR sensors create precise 3D maps that guide drones safely through collapsed structures, dense forests, or hazardous zones. This technology enables smooth navigation, accurate damage visualization, and supports both rescue missions and supply delivery in even the toughest conditions."} />
                </div>
            </section>
        </main>
    )
}

export default Home;
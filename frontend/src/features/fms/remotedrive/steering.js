import React from "react";

const SteeringWheel = ({ rotation, onRotationChange }) => {
  const handleMouseDown = (e) => {
    e.preventDefault();
    const radius = e.target.clientHeight / 2
    const center_x = e.target.getBoundingClientRect().left + radius
    const center_y = e.target.getBoundingClientRect().top + radius

    const clickX = e.clientX - center_x
    const clickY = e.clientY - center_y
    const clickRotation = 180 - (Math.atan2(clickX, clickY) * 180) / Math.PI

    var lastRotation = clickRotation
    var currentRotation = 0

    const handleMouseMove = (e) => {
      /* The maximum steering offset */
      let max_offset = 22.5

      /* Calculate the new angle responds to the center */
      const deltaX = e.clientX - center_x
      const deltaY = e.clientY - center_y
      const newRotation = 180 - (Math.atan2(deltaX, deltaY) * 180) / Math.PI

      /* Post Process of the rotate angle */
      /* 1. Rotation cross the 0-degree */
      let deltaRotation = newRotation - lastRotation
      if(newRotation - lastRotation > 180){ /* Rotate to left corss 0-degree */
        deltaRotation = newRotation - (lastRotation + 360)
      }
      else if(newRotation - lastRotation < -180){ /* Rotate to right cross 0-degree */
        deltaRotation = (360 + newRotation) - lastRotation
      }
      
      /* 2. Make the angle to not exceed the maximum offset */
      let targetRotation = currentRotation + deltaRotation
      if(targetRotation > max_offset) targetRotation = max_offset;
      else if(targetRotation < -max_offset) targetRotation = -max_offset;
      lastRotation = newRotation
      currentRotation = targetRotation
      onRotationChange(targetRotation);
    };

    const handleMouseUp = () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      onRotationChange(0)
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

  return (
    <div
      onMouseDown={handleMouseDown}
      style={{ cursor: "grab" }}
    >
      <img
        className="h-40"
        src={require('./steering-wheel.png')}
        alt="Steering Wheel"
        style={{
          transform: `rotate(${rotation}deg)`,
        }}
      />
    </div>
  );
}

export default SteeringWheel;
